window.myScriptData = {
    clientId: '2ee3a95a1ded4fd59e957d548bc837a3',
    API_BASE_URL: 'https://api.chat.peepul.org'
};

(function (w, d, s, f, js, fjs) {
    js = d.createElement(s);
    fjs = d.getElementsByTagName(s)[0];
    js.async = 1;
    js.src = f;
    js.id = 'myWidgetScript';
    fjs.parentNode.insertBefore(js, fjs);
}(window, document, 'script', 'https://api.chat.peepul.org/api/v2/popupbot/js'));