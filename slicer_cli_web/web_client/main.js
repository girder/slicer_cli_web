import { registerPluginNamespace } from '@girder/core/pluginUtils';

// expose symbols under girder.plugins
import * as slicer_cli_web from './index';
registerPluginNamespace('slicer_cli_web', slicer_cli_web);