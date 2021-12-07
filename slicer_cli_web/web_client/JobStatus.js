import JobStatus from '@girder/jobs/JobStatus';

const jobPluginIsCancelable = JobStatus.isCancelable;
JobStatus.isCancelable = function (job) {
    if (job.get('type').startsWith('slicer_cli_web_batch')) {
        return ![JobStatus.CANCELED, JobStatus.WORKER_CANCELING || 824,
            JobStatus.SUCCESS, JobStatus.ERROR].includes(job.get('status'));
    }
    return jobPluginIsCancelable(job);
};
