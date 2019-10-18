import View from '@girder/core/views/View';

import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import { restRequest } from '@girder/core/rest';
import events from '@girder/core/events';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

/**
 * Show the default quota settings for users and collections.
 */
const ConfigView = View.extend({
    events: {
        'submit #g-slicer-cli-web-form': function (event) {
            event.preventDefault();
            this.$('#g-slicer-cli-web-error-message').empty();
            this._saveSettings([{
                key: 'slicer_cli_web.task_folder',
                value: this.$('.g--slicer-cli-web-task-folder').val()
            }]);
        }
    },
    initialize: function () {
        ConfigView.getSettings((settings) => {
            this.settings = settings;
            this.render();
        });
    },

    render: function () {
        this.$el.html(ConfigViewTemplate({
            settings: this.settings,
            viewers: ConfigView.viewers
        }));
        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Slicer CLI Web',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    },

    _saveSettings: function (settings) {
        /* Now save the settings */
        return restRequest({
            type: 'PUT',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(() => {
            /* Clear the settings that may have been loaded. */
            ConfigView.clearSettings();
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-slicer-cli-web-error-message').text(
                resp.responseJSON.message
            );
        });
    }
}, {
    /* Class methods and objects */

    /* The list of viewers is added as a property to the select widget view so
     * that it is also available to the settings page. */
    viewers: [
        {
            name: 'geojs',
            label: 'GeoJS',
            type: 'geojs'
        }, {
            name: 'openseadragon',
            label: 'OpenSeaDragon',
            type: 'openseadragon'
        }, {
            name: 'openlayers',
            label: 'OpenLayers',
            type: 'openlayers'
        }, {
            name: 'leaflet',
            label: 'Leaflet',
            type: 'leaflet'
        }, {
            name: 'slideatlas',
            label: 'SlideAtlas',
            type: 'slideatlas'
        }
    ],

    /**
     * Get settings if we haven't yet done so.  Either way, call a callback
     * when we have settings.
     *
     * @param {function} callback a function to call after the settings are
     *      fetched.  If the settings are already present, this is called
     *      without any delay.
     */
    getSettings: function (callback) {
        if (!ConfigView.settings) {
            restRequest({
                type: 'GET',
                url: 'large_image/settings'
            }).done((resp) => {
                ConfigView.settings = resp;
                if (callback) {
                    callback(ConfigView.settings);
                }
            });
        } else {
            if (callback) {
                callback(ConfigView.settings);
            }
        }
    },

    /**
     * Clear the settings so that getSettings will refetch them.
     */
    clearSettings: function () {
        delete ConfigView.settings;
    }
});

export default ConfigView;
