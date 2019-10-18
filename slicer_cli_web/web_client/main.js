import { registerPluginNamespace } from '@girder/core/pluginUtils';

// import modules for side effects
import './routes';
import './views/ItemView';
import './views/CollectionView';

// expose symbols under girder.plugins
import * as slicer_cli_web from './index';
registerPluginNamespace('slicer_cli_web', slicer_cli_web);