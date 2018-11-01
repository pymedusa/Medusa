<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-email" title="Email"></span>
            <h3><app-link href="https://en.wikipedia.org/wiki/Comparison_of_webmail_providers">Email</app-link></h3>
            <p>Allows configuration of email notifications on a per show basis.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_telegram" :explanations="['Send email notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-email">

                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="telegram_notify_onsnatch" :explanations="['Send a message when a download starts??']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="telegram_notify_ondownload" :explanations="['send a message when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="telegram_notify_onsubtitledownload" :explanations="['send a message when subtitles are downloaded?']" @change="save()"/>
                    <config-textbox v-model="host" label="SMTP host" id="email_host" :explanations="['hostname of your SMTP email server.']" @change="save()"/>
                    <config-textbox-number :min="1" :step="1" v-model="port" label="SMTP port" id="email_port" :explanations="['port number used to connect to your SMTP host.']" @change="save()"/>
                    <config-textbox v-model="from" label="SMTP from" id="email_from" :explanations="['sender email address, some hosts require a real address.']" @change="save()"/>
                    <config-toggle-slider v-model="tls" label="Use TLS" id="email_tls" :explanations="['check to use TLS encryption.']" @change="save()"/>
                    <config-textbox v-model="username" label="SMTP username" id="email_username" :explanations="['(optional) your SMTP server username.']" @change="save()"/>
                    <config-textbox v-model="password" label="SMTP password" id="email_password" :explanations="['(optional) your SMTP server password.']" @change="save()"/>

                    <config-template label-for="email_list" label="Global email list">
                        <select-list name="email_list" id="email_list" :list-items="addressList" @change="emailUpdateAddressList"/>
                        Email addresses listed here, will receive notifications for <b>all</b> shows.<br>
                        (This field may be blank except when testing.)
                    </config-template>

                    <config-textbox
                        v-model="subject"
                        label="Email Subject"
                        id="email_subject"
                        :explanations="['Use a custom subject for some privacy protection?<br>', '(Leave blank for the default Medusa subject)']"
                        @change="save()"
                    />

                    <config-template label-for="email_show" label="Show notification list">
                        <show-selector select-class="form-control input-sm max-input350" placeholder="-- Select a Show --" @change="emailUpdateShowEmail($event)"/>
                    </config-template>

                    <div class="form-group">
                        <div class="row">
                            <!-- bs3 and 4 -->
                            <div class="offset-sm-2 col-sm-offset-2 col-sm-10 content">
                                <select-list name="email_list" id="email_list" :list-items="selectedShowAdresses" @change="savePerShowNotifyList('email')" @update="selectedShowAdresses = $event"/>
                                Email addresses listed here, will receive notifications for <b>all</b> shows.<br>
                                (This field may be blank except when testing.)
                            </div>
                        </div>
                    </div>

                    <div class="testNotification" id="testEmail-result">Click below to test.</div>
                    <input class="btn-medusa" type="button" value="Test Email" id="testEmail" @click="test"/>
                    <input class="btn-medusa config_submitter" type="submit" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'email',
    data: () => ({
        selectedShow: null,
        selectedShowAdresses: [],
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        host: null,
        port: null,
        from: null,
        tls: null,
        username: null,
        password: null,
        addressList: [],
        subject: null
    }),
    methods: {
        save() {},
        test() {
            let to = '';
            const status = $('#testEmail-result');
            status.html(MEDUSA.config.loading);
            let host = $('#email_host').val();
            host = host.length > 0 ? host : null;
            let port = $('#email_port').val();
            port = port.length > 0 ? port : null;
            const tls = $('#email_tls').find('input').is(':checked') ? 1 : 0;
            let from = $('#email_from').val();
            from = from.length > 0 ? from : 'root@localhost';
            const user = $('#email_username').val().trim();
            const pwd = $('#email_password').val();
            let err = '';
            if (host === null) {
                err += '<li style="color: red;">You must specify an SMTP hostname!</li>';
            }
            if (port === null) {
                err += '<li style="color: red;">You must specify an SMTP port!</li>';
            } else if (port.match(/^\d+$/) === null || parseInt(port, 10) > 65535) {
                err += '<li style="color: red;">SMTP port must be between 0 and 65535!</li>';
            }
            if (err.length > 0) {
                err = '<ol>' + err + '</ol>';
                status.html(err);
            } else {
                to = prompt('Enter an email address to send the test to:', null); // eslint-disable-line no-alert
                if (to === null || to.length === 0 || to.match(/.*@.*/) === null) {
                    status.html('<p style="color: red;">You must provide a recipient email address!</p>');
                } else {
                    $.get('home/testEmail', {
                        host,
                        port,
                        smtp_from: from, // eslint-disable-line camelcase
                        use_tls: tls, // eslint-disable-line camelcase
                        user,
                        pwd,
                        to
                    }, msg => {
                        $('#testEmail-result').html(msg);
                    });
                }
            }
        },
        emailUpdateShowEmail(selectedShow) {
            this.emailSelectedShow = selectedShow;
            apiRoute('home/loadShowNotifyLists').then(({ data }) => {
                if (data._size > 0) {
                    const list = data[selectedShow].list ? data[selectedShow].list.split(',') : [];
                    this.emailSelectedShowAdresses = selectedShow ? list : [];
                }
            });
        },
        emailUpdateAddressList(items) {
            this.addressList = items.map(x => x.value);
        },
        savePerShowNotifyList(listType) {
            const {
                selectedShow,
                updateShowEmail,
                selectedShowAdresses
            } = this;

            let form = new FormData();
            let reloadList = emailUpdateShowEmail;
            form.set('show', emailSelectedShow);
            form.set('emails', emailSelectedShowAdresses);

            // Save the list
            apiRoute.post('home/saveShowNotifyList', form);
        }
    }
}
</script>

<style>

</style>
