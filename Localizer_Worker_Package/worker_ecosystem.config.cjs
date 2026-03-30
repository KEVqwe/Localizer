module.exports = {
  apps: [
    {
      name: "localizer-remote-worker",
      // Colleague's environment Python/Celery path will be auto-set by the installer
      script: "celery",
      args: "-A worker.src.celery_tasks worker --loglevel=info -P solo",
      windowsHide: true,
      watch: false,
      autorestart: true,
      env: {
        // Force worker to use the local environment's python paths
        PYTHONPATH: "."
      }
    }
  ]
};
