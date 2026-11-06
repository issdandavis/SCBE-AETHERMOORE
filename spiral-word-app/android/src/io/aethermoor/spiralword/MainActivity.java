package io.aethermoor.spiralword;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.net.Uri;
import android.util.Base64;
import android.webkit.*;
import android.view.View;
import org.json.JSONObject;
import java.io.*;
import java.util.*;
import java.net.HttpURLConnection;
import java.net.URL;

/** Offline writing desk. Only packaged assets can reach the file-save bridge. */
public class MainActivity extends Activity {
    private WebView web;
    private ValueCallback<Uri[]> chooser;
    private byte[] pendingFile;
    private static final int SAVE = 71, OPEN = 72;
    private static final String ORIGIN = "app.spiralword.local";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        web = new WebView(this);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false);
        // This development APK supports local UI inspection.
        WebView.setWebContentsDebuggingEnabled(true);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                return !local(req.getUrl());
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                Uri url = req.getUrl();
                if (!local(url)) return missing();
                String name = url.getPath();
                if (name == null || name.equals("/")) name = "/index.html";
                if (!Arrays.asList("/index.html", "/core.js", "/app.js", "/style.css", "/profile.json").contains(name)) return missing();
                String mime = name.endsWith(".js") ? "text/javascript" : name.endsWith(".css") ? "text/css" : name.endsWith(".json") ? "application/json" : "text/html";
                try { return new WebResourceResponse(mime, "UTF-8", getAssets().open("mla" + name)); }
                catch (IOException e) { return missing(); }
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (chooser != null) chooser.onReceiveValue(null);
                chooser = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE); intent.setType("application/json");
                startActivityForResult(intent, OPEN);
                return true;
            }
        });
        web.addJavascriptInterface(new Files(), "AndroidFiles");
        setContentView(web);
        web.setOnApplyWindowInsetsListener((v, insets) -> {
            v.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(), insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });
        web.loadUrl("https://" + ORIGIN + "/index.html");
    }

    private boolean local(Uri url) {
        return "https".equals(url.getScheme()) && ORIGIN.equals(url.getHost()) && (url.getPort() == -1 || url.getPort() == 443);
    }
    private WebResourceResponse missing() {
        return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", Collections.emptyMap(), new ByteArrayInputStream(new byte[0]));
    }
    private void report(boolean ok, String message) {
        web.evaluateJavascript("window.onNativeSave(" + ok + "," + JSONObject.quote(message) + ")", null);
    }
    public class Files {
        @JavascriptInterface public void api(String base, String token, String operation, String document) {
            if (!operation.equals("profile") && !operation.equals("validate")) return;
            if (document.length() > 1500000 || token.length() > 8192 || token.indexOf('\n') >= 0 || token.indexOf('\r') >= 0) return;
            new Thread(() -> {
                HttpURLConnection connection = null;
                try {
                    URL url = new URL(base.replaceAll("/+$", "") + "/" + operation);
                    boolean loopback = url.getHost().equals("127.0.0.1") || url.getHost().equals("localhost");
                    if (!url.getProtocol().equals("https") && !(loopback && url.getProtocol().equals("http"))) throw new IOException();
                    if (url.getUserInfo() != null || url.getRef() != null || url.getQuery() != null) throw new IOException();
                    connection = (HttpURLConnection) url.openConnection();
                    connection.setInstanceFollowRedirects(false);
                    connection.setConnectTimeout(5000); connection.setReadTimeout(5000);
                    if (!token.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + token);
                    if (operation.equals("validate")) {
                        connection.setRequestMethod("POST"); connection.setDoOutput(true);
                        connection.setRequestProperty("Content-Type", "application/json");
                        try (OutputStream s = connection.getOutputStream()) { s.write(document.getBytes("UTF-8")); }
                    }
                    if (connection.getResponseCode() != 200) throw new IOException();
                    ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                    try (InputStream stream = connection.getInputStream()) {
                        byte[] buffer = new byte[4096]; int n;
                        while ((n = stream.read(buffer)) != -1) { bytes.write(buffer, 0, n); if (bytes.size() > 65536) throw new IOException(); }
                    }
                    String json = new String(bytes.toByteArray(), "UTF-8");
                    new JSONObject(json); // Only JSON objects may cross back into the packaged UI.
                    runOnUiThread(() -> web.evaluateJavascript("window.onNativeApi(true," + JSONObject.quote(json) + ")", null));
                } catch (Exception e) {
                    runOnUiThread(() -> web.evaluateJavascript("window.onNativeApi(false,'API unavailable. Check the URL, token, and connection.')", null));
                } finally { if (connection != null) connection.disconnect(); }
            }, "spiralword-api").start();
        }
        @JavascriptInterface public void save(String name, String mime, String data) {
            runOnUiThread(() -> {
                if (pendingFile != null) { report(false, "Finish the current save first."); return; }
                if (!mime.equals("application/json") && !mime.equals("application/vnd.openxmlformats-officedocument.wordprocessingml.document")) { report(false, "Unsupported file type."); return; }
                if (data.length() > 12000000) { report(false, "Document is too large to export."); return; }
                try {
                    pendingFile = Base64.decode(data, Base64.DEFAULT);
                    String safe = name.replaceAll("[\\\\/:*?\"<>|\\p{Cntrl}]", "_");
                    Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE); intent.setType(mime); intent.putExtra(Intent.EXTRA_TITLE, safe);
                    startActivityForResult(intent, SAVE);
                } catch (RuntimeException e) { pendingFile = null; report(false, "Could not open the file picker."); }
            });
        }
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == OPEN && chooser != null) {
            chooser.onReceiveValue(result == RESULT_OK && data != null ? new Uri[]{data.getData()} : null); chooser = null;
        }
        if (request == SAVE) {
            if (result == RESULT_OK && data != null && pendingFile != null) {
                try (OutputStream stream = getContentResolver().openOutputStream(data.getData())) {
                    if (stream == null) throw new IOException();
                    stream.write(pendingFile); report(true, "File saved. You can upload it in Canvas.");
                } catch (IOException | RuntimeException e) { report(false, "Save failed. Your draft is still here; try another folder."); }
            } else report(false, "Save cancelled. Your draft is still here.");
            pendingFile = null;
        }
    }
    @Override protected void onDestroy() { if (chooser != null) chooser.onReceiveValue(null); web.destroy(); super.onDestroy(); }
}
