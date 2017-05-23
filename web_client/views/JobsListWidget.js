import View from 'girder/views/View';
import { SORT_DESC } from 'girder/constants';
import eventStream from 'girder/utilities/EventStream';

import JobCollection from 'girder_plugins/jobs/collections/JobCollection';
import JobStatus from 'girder_plugins/jobs/JobStatus';

import jobListWidget from '../templates/jobListWidget.pug';
// import '../stylesheets/jobListWidget.styl';

const JobsListWidget = View.extend({
    initialize() {
        if (!this.collection) {
            this.collection = new JobCollection();
            this.collection.pageLimit = 10;
            this.collection.sortDir = SORT_DESC;
            this.collection.sortField = 'created';
        }

        this.listenTo(this.collection, 'all', this.render);
        this.listenTo(eventStream, 'g:event.job_status', this.fetchAndRender);
        this.listenTo(eventStream, 'g:event.job_created', this.fetchAndRender);
        this.fetchAndRender();
    },

    render() {
        const jobs = this.collection.filter((job) => {
            return job.get('title').match(/HistomicsTK\./);
        }).map((job) => job.attributes);

        this.$el.html(jobListWidget({
            jobs,
            JobStatus
        }));
    },

    fetchAndRender() {
        this.collection.fetch(null, true)
            .then(() => this.render());
    }
});

export default JobsListWidget;
