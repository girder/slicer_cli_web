// We export these symbols for backwards compatibility since they used to live
// in this plugin. TODO remove in future versions
import ControlWidget from 'girder_plugins/item_tasks/views/ControlWidget';
import ControlsPanel from 'girder_plugins/item_tasks/views/ControlsPanel';
import ItemSelectorWidget from 'girder_plugins/item_tasks/views/ItemSelectorWidget';
import Panel from 'girder_plugins/item_tasks/views/Panel';
import JobsPanel from './JobsPanel';
import PanelGroup from './PanelGroup';

export {
    ControlWidget,
    ControlsPanel,
    ItemSelectorWidget,
    JobsPanel,
    Panel,
    PanelGroup
};
