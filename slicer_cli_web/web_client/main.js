import { registerPluginNamespace } from '@girder/core/pluginUtils';

// import modules for side effects
import './routes';
import './views/ItemView';
import './views/CollectionView';
import './JobStatus';

// expose symbols under girder.plugins
import * as slicerCLIWeb from './index';
registerPluginNamespace('slicer_cli_web', slicerCLIWeb);
