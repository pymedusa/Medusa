<%inherit file="/layouts/main.mako"/>
<script>
let app;
const startVue = () => {
    app = new Vue({
        el: '#vue-wrap',
        data() {
            return {};
        }
    });
};
</script>
</%block>
<%block name="content">
<h1 class="header">${header}</h1>
<div class="align-center">
You have reached this page by accident, please check the url.
</div>
</%block>
