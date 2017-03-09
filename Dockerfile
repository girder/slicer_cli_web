FROM ubuntu:16.04
MAINTAINER Deepak Roy Chittajallu <deepk.chittajallu@kitware.com>

# Install system pre-requisites
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    wget \
    git \
    emacs vim \
    make cmake cmake-curses-gui \
    ninja-build && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Working directory
ENV BUILD_PATH=$PWD/build

# Install miniconda
RUN mkdir -p $BUILD_PATH && \
    wget https://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh \
    -O $BUILD_PATH/install_miniconda.sh && \
    bash $BUILD_PATH/install_miniconda.sh -b -p $BUILD_PATH/miniconda && \
    rm $BUILD_PATH/install_miniconda.sh && \
    chmod -R +r $BUILD_PATH && \
    chmod +x $BUILD_PATH/miniconda/bin/python
ENV PATH=$BUILD_PATH/miniconda/bin:${PATH}

# Install CMake
ENV CMAKE_ARCHIVE_SHA256 fdda4a8324e23c705ef0c2c45ba934ff3bd43798fb5631eec2d453693dbe777c
ENV CMAKE_VERSION_MAJOR 3
ENV CMAKE_VERSION_MINOR 6
ENV CMAKE_VERSION_PATCH 1
ENV CMAKE_VERSION ${CMAKE_VERSION_MAJOR}.${CMAKE_VERSION_MINOR}.${CMAKE_VERSION_PATCH}
RUN cd $BUILD_PATH && \
  wget https://cmake.org/files/v${CMAKE_VERSION_MAJOR}.${CMAKE_VERSION_MINOR}/cmake-${CMAKE_VERSION}-Linux-x86_64.tar.gz && \
  hash=$(sha256sum ./cmake-${CMAKE_VERSION}-Linux-x86_64.tar.gz | awk '{ print $1 }') && \
  [ $hash = "${CMAKE_ARCHIVE_SHA256}" ] && \
  tar -xzvf cmake-${CMAKE_VERSION}-Linux-x86_64.tar.gz && \
  rm cmake-${CMAKE_VERSION}-Linux-x86_64.tar.gz
ENV PATH=$BUILD_PATH/cmake-${CMAKE_VERSION}-Linux-x86_64/bin:${PATH}

# Disable "You are in 'detached HEAD' state." warning
RUN git config --global advice.detachedHead false

# Download/configure/build/install ITK for SlicerExecutionModel (needed only for C++ CLIs)
ENV ITK_GIT_TAG v4.10.0
RUN cd $BUILD_PATH && git clone --depth 1 -b ${ITK_GIT_TAG} git://itk.org/ITK.git && \
    mkdir ITK-build && \
    cd ITK-build && \
    cmake \
        -G Ninja \
        -DCMAKE_INSTALL_PREFIX:PATH=/usr \
        -DBUILD_EXAMPLES:BOOL=OFF \
        -DBUILD_TESTING:BOOL=OFF \
        -DBUILD_SHARED_LIBS:BOOL=ON \
        -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
        -DITK_LEGACY_REMOVE:BOOL=ON \
        -DITK_BUILD_DEFAULT_MODULES:BOOL=OFF \
        -DITK_USE_SYSTEM_LIBRARIES:BOOL=OFF \
        -DModule_ITKCommon:BOOL=ON \
        -DModule_ITKIOXML:BOOL=ON \
        -DModule_ITKExpat:BOOL=ON \
        ../ITK && \
    ninja install && \
    cd $BUILD_PATH && rm -rf ITK ITK-build

# Download/configure/build SlicerExecutionModel (needed only for C++ CLIs)
ENV SEM_GIT_TAG 7525fc777a064529aff55e41aef6d91a85074553
RUN cd $BUILD_PATH && \
    git clone git://github.com/Slicer/SlicerExecutionModel.git && \
    (cd SlicerExecutionModel && git checkout ${SEM_GIT_TAG}) && \
    mkdir SEM-build && cd SEM-build && \
    cmake \
        -G Ninja \
        -DCMAKE_BUILD_TYPE:STRING=Release \
        -DBUILD_TESTING:BOOL=OFF \
        ../SlicerExecutionModel && \
    ninja

# Install ctk-cli
RUN conda install --yes -c cdeepakroy ctk-cli=1.4.1

# copy slicer_cli_web files
ENV slicer_cli_web_path=$BUILD_PATH/slicer_cli_web
RUN mkdir -p $slicer_cli_web_path
COPY . $slicer_cli_web_path/
WORKDIR $slicer_cli_web_path/server