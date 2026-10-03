/**
 * cs-benha-schedule upload endpoint (T12) — Google Apps Script web app.
 *
 * Deploy: script.google.com → New project → paste this file → Project
 * Settings → Script Properties (server-side ONLY, never in page source):
 *   PASSCODE_HASH = hex(SHA-256(passcode))   // client hashes before sending
 *   GITHUB_PAT    = fine-grained PAT (contents:write on this repo only)
 *   GITHUB_REPO   = "owner/cs-benha-schedule"
 *   GITHUB_BRANCH = "main"
 *   PDF_PATH      = "pdf/جدول-العام.pdf"
 * Deploy → New deployment → Web app → Execute as: Me → Access: Anyone.
 * Paste the /exec URL into the site's update dialog / README.
 *
 * POST JSON: {passcode_hash, filename, mime, content_base64}
 * Uses the Git Data API (Contents API caps ~1MB after base64).
 */

var MAX_BYTES = 5 * 1024 * 1024;
var RATE_PER_MINUTE = 5;

function scriptProps() {
  return PropertiesService.getScriptProperties();
}

function jsonOut(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(
    ContentService.MimeType.JSON
  );
}

function checkRate_() {
  var cache = CacheService.getScriptCache();
  var count = Number(cache.get('upload_count') || 0);
  if (count >= RATE_PER_MINUTE) return false;
  cache.put('upload_count', String(count + 1), 60);
  return true;
}

function gh_(method, path, payload, token) {
  var options = {
    method: method,
    muteHttpExceptions: true,
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
  };
  if (payload) {
    options.contentType = 'application/json';
    options.payload = JSON.stringify(payload);
  }
  var res = UrlFetchApp.fetch('https://api.github.com' + path, options);
  var code = res.getResponseCode();
  if (code < 200 || code >= 300) {
    throw new Error('GitHub ' + method + ' ' + path + ' → ' + code + ': ' + res.getContentText().slice(0, 200));
  }
  return JSON.parse(res.getContentText() || '{}');
}

function doGet() {
  return jsonOut({ ok: true, service: 'cs-benha-schedule-upload' });
}

function doPost(e) {
  try {
    if (!checkRate_()) {
      return jsonOut({ ok: false, error: 'rate-limited, try again in a minute' });
    }
    var body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    var props = scriptProps();

    var want = String(props.getProperty('PASSCODE_HASH') || '').toLowerCase();
    var got = String(body.passcode_hash || '').toLowerCase();
    if (!want || got !== want) {
      return jsonOut({ ok: false, error: 'bad passcode' });
    }
    if (body.mime !== 'application/pdf' || !/\.pdf$/i.test(String(body.filename || ''))) {
      return jsonOut({ ok: false, error: 'only .pdf uploads are accepted' });
    }
    var bytes = Utilities.base64Decode(String(body.content_base64 || ''));
    if (bytes.length === 0 || bytes.length > MAX_BYTES) {
      return jsonOut({ ok: false, error: 'pdf must be 1 byte..5MB' });
    }

    var token = props.getProperty('GITHUB_PAT');
    var repo = props.getProperty('GITHUB_REPO');
    var branch = props.getProperty('GITHUB_BRANCH') || 'main';
    var pdfPath = props.getProperty('PDF_PATH') || 'pdf/schedule.pdf';
    if (!token || !repo) throw new Error('server misconfigured (PAT/repo)');

    // Git Data API: ref → commit → tree → blob → tree → commit → ref.
    var ref = gh_('get', '/repos/' + repo + '/git/ref/heads/' + branch, null, token);
    var baseSha = ref.object.sha;
    var baseCommit = gh_('get', '/repos/' + repo + '/git/commits/' + baseSha, null, token);
    var blob = gh_('post', '/repos/' + repo + '/git/blobs', {
      content: Utilities.base64Encode(bytes),
      encoding: 'base64',
    }, token);
    var tree = gh_('post', '/repos/' + repo + '/git/trees', {
      base_tree: baseCommit.tree.sha,
      tree: [{ path: pdfPath, mode: '100644', type: 'blob', sha: blob.sha }],
    }, token);
    var d = new Date();
    var stamp = d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2);
    var commit = gh_('post', '/repos/' + repo + '/git/commits', {
      message: 'update: schedule pdf ' + stamp + ' (via site upload)',
      tree: tree.sha,
      parents: [baseSha],
    }, token);
    gh_('patch', '/repos/' + repo + '/git/refs/heads/' + branch, { sha: commit.sha }, token);

    // A PAT commit (not GITHUB_TOKEN) auto-triggers update.yml.
    return jsonOut({ ok: true, commit: commit.sha });
  } catch (err) {
    return jsonOut({ ok: false, error: String(err && err.message || err).slice(0, 300) });
  }
}
