

### Configuration

Configuration for the app is handled using pydantic-settings in the `app/settings.py` module. 
Here default values are defined but they can be overridden using environment variables.

e.g. 
```bash
export APP_REDIS_HOST='localhost'
export APP_REDIS_PORT='6379'
```

### Local Redis

```bash
redis-server
```

### Run
Run the app from the root directory with the following command:
```
uvicorn app.app:app --reload --port 8000
```
To run locally and test using the swagger docs UI you can disable auth middleware with: 
```bash
APP_DISABLE_AUTH_MIDDLEWARE=1 uvicorn app.app:app --reload --port 8000
```

