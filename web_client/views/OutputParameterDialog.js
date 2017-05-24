import View from 'girder/views/View';

import outputParameterDialog from '../templates/outputParameterDialog.pug';

const OutputParameterDialog = View.extend({
    initialize(settings) {
        this.parameters = settings.parameters;
    },

    render() {
        this.$el.html(
            outputParameterDialog({
                parameters: this.parameters
            })
        ).girderModal(this);
    }
});

export default OutputParameterDialog;
