# Colab Local Connection Reference

For Colab local runtime connections:

1. Start your notebook in a local runtime mode.
2. Run the cell that exposes local connection details.
3. Copy backend URL value:

```text
http://127.0.0.1:8888/?token=<TOKEN>
```

4. Do **not** paste the URL with token into shared chat logs.
5. Run `--set` once and persist metadata in `%USERPROFILE%\.scbe\colab_n8n_bridge.json`.
6. Keep reusable secrets in Sacred Tongue local store:

- `SCBE_COLAB_BACKEND_URL_<PROFILE>`
- `SCBE_COLAB_TOKEN_<PROFILE>`

Run:

```powershell
python skills/clawhub/scbe-colab-n8n-bridge/scripts/colab_n8n_bridge.py --set --name pivot --backend-url "<BACKEND_URL>"
```
