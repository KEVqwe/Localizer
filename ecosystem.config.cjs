module.exports = {
  apps: [
    {
      name: "localizer-redis",
      script: "docker-compose",
      args: "up -d",
      autorestart: false,
      watch: false
    },
    {
      name: "localizer-backend",
      script: "C:\\Users\\TU\\miniconda3\\envs\\py311\\python.exe",
      args: "-m server.src.main",
      env: {
        PYTHONPATH: "."
      },
      windowsHide: true,
      watch: false,
      autorestart: true
    },
    {
      name: "localizer-worker",
      script: "C:\\Users\\TU\\miniconda3\\envs\\py311\\Scripts\\celery.exe",
      args: "-A worker.src.celery_tasks worker --loglevel=info -P solo",
      windowsHide: true,
      watch: false,
      autorestart: true
    }
  ]
};
