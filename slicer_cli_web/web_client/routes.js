import events from '@girder/core/events';
import router from '@girder/core/router';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

import ConfigView from './views/ConfigView';

exposePluginConfig('slicer_cli_web', 'plugins/slicer_cli_web/config');

router.route('plugins/slicer_cli_web/config', 'slicerCLIWebConfig', () => {
    events.trigger('g:navigateTo', ConfigView);
});
