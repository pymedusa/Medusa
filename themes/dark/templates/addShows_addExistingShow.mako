<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
%>
<%block name="scripts">
<script type="text/javascript" src="js/add-show-options.js?${sbPID}"></script>
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Existing Show'
        },
        data() {
            return {
                header: 'Existing Show',
                lastTxt: ''
            };
        },
        mounted() {
            // Need to delay that a bit
            this.$nextTick(() => {
                // Hide the black/whitelist, because it can only be used for a single anime show
                $.updateBlackWhiteList(undefined);
            });
            this.rootDirStaticList();
            this.loadContent();

            $('#tableDiv').on('click', '#checkAll', event => {
                $('.showDirCheck').each((index, element) => {
                    element.checked = event.currentTarget.checked;
                });
            });
            $('#rootDirStaticList').on('click', '.rootDirCheck', this.loadContent);
            /* @TODO: Fix this.
             * It should reload root dirs after changing them, without needing to refresh the page.
             * Currently doesn't work.
             */
            $(document.body).on('change', '#rootDirText', () => {
                if (this.lastTxt === $('#rootDirText').val()) {
                    return false;
                }
                this.lastTxt = $('#rootDirText').val();
                this.rootDirStaticList();
                this.loadContent();
            });
        },
        methods: {
            rootDirStaticList() {
                $('#rootDirStaticList').html('');
                $('#rootDirs option').each((index, element) => {
                    $('#rootDirStaticList').append('<li class="ui-state-default ui-corner-all"><input type="checkbox" class="rootDirCheck" id="' + $(element).val() + '" checked="checked"> <label for="' + $(element).val() + '"><b>' + $(element).val() + '</b></label></li>');
                });
            },
            loadContent() {
                let url_query = '';
                $('.rootDirCheck').each((index, element) => {
                    if ($(element).is(':checked')) {
                        if (url_query.length !== 0) {
                            url_query += '&';
                        }
                        url_query += 'rootDir=' + encodeURIComponent($(element).attr('id'));
                    }
                });

                $('#tableDiv').html('<img id="searchingAnim" src="images/loading32.gif" height="32" width="32" /> loading folders...');
                $.get('addShows/massAddTable/', url_query, data => {
                    $('#tableDiv').html(data);
                    $('#addRootDirTable').tablesorter({
                        // SortList: [[1,0]],
                        widgets: ['zebra'],
                        headers: {
                            0: { sorter: false }
                        }
                    });
                });
            },
            submitShowDirs() {
                const dirArr = [];
                $('.showDirCheck').each((index, element) => {
                    if (element.checked === true) {
                        const originalIndexer = $(element).attr('data-indexer');
                        let indexerId = '|' + $(element).attr('data-indexer-id');
                        const showName = $(element).attr('data-show-name');
                        const showDir = $(element).attr('data-show-dir');

                        const indexer = $(element).closest('tr').find('select').val();
                        if (originalIndexer !== indexer || originalIndexer === '0') {
                            indexerId = '';
                        }
                        dirArr.push(encodeURIComponent(indexer + '|' + showDir + indexerId + '|' + showName));
                    }
                });

                if (dirArr.length === 0) {
                    return false;
                }

                window.location.href = $('base').attr('href') + 'addShows/addExistingShows?promptForSettings=' + ($('#promptForSettings').prop('checked') ? 'on' : 'off') + '&shows_to_add=' + dirArr.join('&shows_to_add=');
            }
        }
    });
};
</script>
</%block>
<%block name="content">
<h1 class="header">{{header}}</h1>
<div id="newShowPortal">
    <div id="config-components">
        <ul><li><app-link href="#core-component-group1">Add Existing Show</app-link></li></ul>
        <div id="core-component-group1" class="tab-pane active component-group">
            <form id="addShowForm" method="post" action="addShows/addExistingShows" accept-charset="utf-8">
                <div id="tabs">
                    <ul>
                        <li><app-link href="addShows/existingShows/#tabs-1">Manage Directories</app-link></li>
                        <li><app-link href="addShows/existingShows/#tabs-2">Customize Options</app-link></li>
                    </ul>
                    <div id="tabs-1" class="existingtabs">
                        <%include file="/inc_rootDirs.mako"/>
                    </div>
                    <div id="tabs-2" class="existingtabs">
                        <%include file="/inc_addShowOptions.mako"/>
                    </div>
                </div>
                <br>
                <p>Medusa can add existing shows, using the current options, by using locally stored NFO/XML metadata to eliminate user interaction.
                If you would rather have Medusa prompt you to customize each show, then use the checkbox below.</p>
                <p><input type="checkbox" name="promptForSettings" id="promptForSettings" /> <label for="promptForSettings">Prompt me to set settings for each show</label></p>
                <hr>
                <p><b>Displaying folders within these directories which aren't already added to Medusa:</b></p>
                <ul id="rootDirStaticList"><li></li></ul>
                <br>
                <div id="tableDiv"></div>
                <br>
                <br>
                <input class="btn-medusa" type="button" value="Submit" id="submitShowDirs" @click="submitShowDirs" />
            </form>
        </div>
    </div>
</div>
</%block>
