/* globals girderTest, describe, it, expect, waitsFor, runs */
girderTest.importPlugin('jobs', 'worker', 'slicer_cli_web');

var slicer;
girderTest.promise.done(function () {
    slicer = girder.plugins.slicer_cli_web;
});

girderTest.startApp();

function login(user, password) {
    girderTest.waitForLoad('login wait 1');
    runs(function () {
        $('.g-login').click();
    });

    girderTest.waitForDialog('login wait 2');
    runs(function () {
        $('#g-login').val(user || 'user');
        $('#g-password').val(password || 'password');
        $('#g-login-button').click();
    });

    waitsFor(function () {
        return $('.g-user-dropdown-link').length > 0;
    }, 'user to be logged in');
    girderTest.waitForLoad('login wait 3');
}



function createCollection(name, description, public, folder){
    var collectionID = false;
    waitsFor(function () {
        var resp = girder.rest.restRequest({
            url: '/collection',
            method: 'POST',
            data: {
                name: name,
                description:description,
                public:public
            },
            async: false
        });
        collectionID = resp.responseJSON["_id"];
        return resp && resp.responseJSON;

    }, "Creating Collection");


    console.log("CollectionId: " + collectionID);
    //Okay now lets take that collectionID and use it to create a sub folder
    var folderID = false;
    waitsFor(function () {
        var resp = girder.rest.restRequest({
            url: '/folder',
            method: 'POST',
            data: {
                name: folder,
                parentType:"collection",
                parentId:collectionID,
                public:public
            },
            async: false
        });
        folderID = resp.responseJSON["_id"];
        return resp && resp.responseJSON;

    }, "Creating SubFolder");


    //Finally we set the default Task folder to the current folder
    waitsFor(function () {
        var resp = girder.rest.restRequest({
            url: '/system/setting',
            method: 'PUT',
            data: {
                key: "slicer_cli_web.task_folder",
                value:folderID
            },
            async: false
        })
        return resp && resp.responseJSON;
    }, "Setting Default Task Folder");    
}
$(function () {
    describe('UploadDockerImages button and functionality', function () {
       
        it('Navigate to Tasks', function () {
            login('admin', 'password');
            createCollection("Tasks","Default Tasks", true, "Slicer CLI Web Tasks");
            waitsFor(function () {
                return $('a.g-nav-link[g-target="collections"]').length > 0;
            }, 'collection list link to load');
            runs(function () {
                $('a.g-nav-link[g-target="collections"]').click();
            });
            waitsFor(function () {
                return $('.g-collection-create-button').length > 0;
            }, 'collection list screen to load');

            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.g-collection-list-entry').length > 0;
            }, 'collection list to load');

            runs(function () {
                $('.g-collection-link').first().click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.g-folder-list-link').length > 0;
            }, 'the folder list to load');
            runs(function () {
                $('.g-folder-list-link').first().click();
            });
            girderTest.waitForLoad();
            runs(function () {                
                expect($('.g-upload-slicer-cli-task-button').length > 0);
                $('.g-upload-slicer-cli-task-button').click();
            });
            girderTest.waitForLoad();

        });
        it('test the upload docker image button', function () {
            waitsFor(function () {
                return $('#g-slicer-cli-web-image').length > 0;
            }, 'the modal dialog to load');

            runs(function () {
                $('#g-slicer-cli-web-image').val('girder/slicer_cli_web:small');
                $('.btn[value="Import Image"]').trigger('click');
            });
            waitsFor(function () {
                var resp = girder.rest.restRequest({
                    url: 'resource/lookup',
                    method: 'GET',
                    data: {path: '/user/admin/Public/girder\\/slicer_cli_web/small/Example1'},
                    async: false
                });
                return resp && resp.responseJSON && resp.responseJSON['_id'];
            }, 'Wait for Example1 to be imported.');
        });
        it('import the small docker', function () {
            runs(function () {
                $('#g-slicer-cli-web-image').val('girder/slicer_cli_web:small');
                $('.btn[value="Import Image"]').trigger('click');
            });
            /*
            waitsFor(function () {
                var resp = girder.rest.restRequest({
                    url: 'resource/lookup',
                    method: 'GET',
                    data: {path: '/user/admin/Public/girder\\/slicer_cli_web/small/Example1'},
                    async: false
                });
                return resp && resp.responseJSON && resp.responseJSON['_id'];
            }, 'Wait for Example1 to be imported.');
                //The folder may be loaded but you need to refresh back to get the new items
            runs(function () {
                expect($('.g-breakcrumb-link').length).toBe(0);
                $('.g-breakcrumb-link').last().trigger('click');
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('g-collection-list-entry').length > 0;
            }, 'collection list to load');
            runs(function () {
                $('.g-collection-link').first().click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                expect($('a.g-folder-list-link:contains("girder/slicer_cli_web")').length).toBe(1);
            });
            */
        });
    })
});