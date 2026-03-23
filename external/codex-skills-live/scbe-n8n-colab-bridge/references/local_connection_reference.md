# Colab Local Connection Notes

- Colab local connection requires notebook runtime on this machine.
- Base URL format is usually:
  - `http://127.0.0.1:8888/?token=abc123`
- Best practice: keep endpoint+token in `%USERPROFILE%\.scbe\colab_n8n_bridge.json` and not in shared command history.
- Validate once with `/api` endpoint from the local bridge script before launching n8n workflows.
