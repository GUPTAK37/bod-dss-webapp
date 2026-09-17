// DSS STANDARD web app frontend: paste the contents of this file into the
// `app.js` slot in the DSS web app editor (Params -> Code).
//
// It resolves the URL of THIS web app's FastAPI backend at runtime (works
// across DSS instances / containers without a hardcoded URL) and embeds
// `/app/` — the FastAPI StaticFiles mount serving the built React bundle —
// in a full-page iframe.

const backendURL = dataiku.getWebAppBackendUrl('app/');

window.onload = function () {
    var ifrm = document.createElement('iframe');
    ifrm.setAttribute('src', backendURL);
    ifrm.setAttribute(
        'style',
        'position:fixed; top:0; left:0; bottom:0; right:0; '
        + 'width:100%; height:100%; border:none; margin:0; padding:0; '
        + 'overflow:hidden;'
    );
    document.body.appendChild(ifrm);
};
