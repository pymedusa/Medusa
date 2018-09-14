<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.providers import sorted_provider_list
    from medusa.providers.generic_provider import GenericProvider
    from medusa.providers.torrent.torznab.torznab import TorznabProvider
%>
<%block name="scripts">
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    beforeMount() {
        $('#config-components').tabs();
    },
    mounted() {
        // @TODO: This needs to be moved to an API function
        function loadProviders() {
            % if app.USE_NZBS:
                % for cur_newznab_provider in app.newznabProviderList:
                    addNewznabProvider('${cur_newznab_provider.get_id()}', '${cur_newznab_provider.name}', '${cur_newznab_provider.url}', '${cur_newznab_provider.api_key}', '${",".join(cur_newznab_provider.cat_ids)}', ${int(cur_newznab_provider.default)});
                % endfor
            % endif
            % if app.USE_TORRENTS:
                % for cur_torrent_rss_provider in app.torrentRssProviderList:
                    addTorrentRssProvider('${cur_torrent_rss_provider.get_id()}', '${cur_torrent_rss_provider.name}', '${cur_torrent_rss_provider.url}', '${cur_torrent_rss_provider.cookies}', '${cur_torrent_rss_provider.title_tag}');
                % endfor
                % for torznab_provider in app.torznab_providers_list:
                    addTorznabProvider('${torznab_provider.get_id()}', '${torznab_provider.name}', '${torznab_provider.url}', '${torznab_provider.api_key}', '${",".join(torznab_provider.cat_ids)}', '${",".join(torznab_provider.cap_tv_search)}');
                % endfor
            % endif
        };

        function showHideProviders() {
            $('.providerDiv').each((index, element) => {
                const providerName = $(element).prop('id');
                const selectedProvider = $('#editAProvider :selected').val();

                if (selectedProvider + 'Div' === providerName) {
                    $(element).show();
                } else {
                    $(element).hide();
                }
            });
        }

        function providerExists(providerList, searchFor) {
            for (let i = 0; i < providerList.length; i++) {
                if (providerList[i].name === searchFor) {
                    console.log('Found ' + providerList[i].name + ' while searching for: ' + searchFor);
                    return true;
                }
            }
            return false;
        };

        /**
        * Gets categories for the provided newznab provider.
        * @param {Array} selectedProvider
        * @return no return data. Function updateNewznabCaps() is run at callback
        */
        function getCategories(kind, selectedProvider) {
            const name = selectedProvider[0];
            const url = selectedProvider[1];
            const apiKey = selectedProvider[2];

            if (!name || !url || !apiKey) {
                return;
            }

            $('.updating_categories').wrapInner('<span><img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif"> Updating Categories...</span>');

            const dfd = new $.Deferred();
            let capabilities = [];

            if (providerExists(znabProvidersCapabilities, name)) {
                $('.updating_categories').empty();
                $('.updating_categories').wrapInner('<span>Categories updated!</span>');
                capabilities = updateCategories([], name);
                dfd.resolve(capabilities);
            } else {
                const params = { kind, url, name, api_key: apiKey }; // eslint-disable-line camelcase
                const jqxhr = $.getJSON('config/providers/getZnabCategories', params);
                jqxhr.always(function(data) {
                    $('.updating_categories').empty();
                    if (data.success === true) {
                        $('.updating_categories').wrapInner('<span>Categories updated!</span>');
                        capabilities = updateCategories(data, name);
                    } else {
                        $('.updating_categories').wrapInner('<span>Updating categories failed!</span>');
                    }
                    dfd.resolve(capabilities);
                });
            }

            return dfd.promise();
        };

        /**
        * Updates the Global array znabProvidersCapabilities with a combination of newznab prov name
        * and category capabilities. Return
        * @param {Array} newzNabCaps, is the returned object with newznabprovider Name and Capabilities.
        * @param {Array} providerName
        * @return no return data. The multiselect input $("#newznab_cap") is updated, as a result.
        */
        function updateCategories(newzNabCaps, providerName) {
            if (newzNabCaps && !providerExists(znabProvidersCapabilities, providerName)) {
                znabProvidersCapabilities.push({
                    name: providerName,
                    categories: newzNabCaps.categories, // eslint-disable-line camelcase
                    params: newzNabCaps.params
                });
            }

            // Loop through the array and if currently selected newznab provider name matches one in the array, use it to
            // update the capabilities select box (on the left).
            const newCapOptions = [];
            let providerParams = '';
            if (providerName) {
                znabProvidersCapabilities.forEach(newzNabCap => {
                    if (newzNabCap.name && newzNabCap.name === providerName && Array.isArray(newzNabCap.categories)) {
                        providerParams = newzNabCap.params;
                        newzNabCap.categories.forEach(categorySet => {
                            if (categorySet.id && categorySet.name) {
                                newCapOptions.push({
                                    value: categorySet.id,
                                    text: categorySet.name + ' (' + categorySet.id + ')'
                                });
                            }
                        });
                    }
                });
            }
            return { categories: newCapOptions, params: providerParams };
        };

        function verifyUrl(url, trailingSlash) {
            trailingSlash = (trailingSlash !== undefined) ? trailingSlash : true; // eslint-disable-line no-negated-condition

            url = $.trim(url);
            if (!url) return;

            if (!/^https?:\/\//i.test(url)) {
                url = 'http://' + url;
            }

            if (trailingSlash && url.match('/$') === null) {
                url += '/';
            }

            return url;
        }

        function addNewznabProvider(id, name, url, apiKey, cats, isDefault) { // eslint-disable-line max-params
            const verifiedUrl = verifyUrl(url);
            if (verifiedUrl === undefined) {
                alert('Invalid URL specified for the "' + name + '" Newznab provider!'); // eslint-disable-line no-alert
            }

            const newData = [isDefault, [name, verifiedUrl, apiKey, cats]];
            newznabProviders[id] = newData;

            $('#editANewznabProvider').append('<option value=' + id + '>' + name + '</option>');

            if ($('#provider_order_list > #' + id).length === 0) {
                $('#provider_order_list').append('<li class="ui-state-default" id="' + id + '"> <input type="checkbox" id="enable_' + id + '" class="provider_enabler" CHECKED> <a href="' + MEDUSA.config.anonURL + url + '" class="imgLink" target="_new"><img src="images/providers/newznab.png" alt="' + name + '" width="16" height="16"></a> ' + name + '</li>'); // eslint-disable-line no-undef
                $('#provider_order_list').sortable('refresh');
            }

            makeNewznabProviderString();
        };

        function addTorrentRssProvider(id, name, url, cookies, titleTag) { // eslint-disable-line max-params
            const verifiedUrl = verifyUrl(url, false);
            if (verifiedUrl === undefined) {
                alert('Invalid URL specified for the "' + name + '" Torrent RSS provider!'); // eslint-disable-line no-alert
            }

            const newData = [name, verifiedUrl, cookies, titleTag];
            torrentRssProviders[id] = newData;

            $('#editATorrentRssProvider').append('<option value=' + id + '>' + name + '</option>');

            if ($('#provider_order_list > #' + id).length === 0) {
                $('#provider_order_list').append('<li class="ui-state-default" id="' + id + '"> <input type="checkbox" id="enable_' + id + '" class="provider_enabler" CHECKED> <a href="' + MEDUSA.config.anonURL + url + '" class="imgLink" target="_new"><img src="images/providers/torrentrss.png" alt="' + name + '" width="16" height="16"></a> ' + name + '</li>'); // eslint-disable-line no-undef
                $('#provider_order_list').sortable('refresh');
            }

            makeTorrentRssProviderString();
        };

        function addTorznabProvider(id, name, url, apiKey, cats, caps) { // eslint-disable-line max-params
            const verifiedUrl = verifyUrl(url);
            if (verifiedUrl === undefined) {
                alert('Invalid URL specified for the "' + name + '" Jackett/Torznab provider!'); // eslint-disable-line no-alert
            }

            const newData = [name, verifiedUrl, apiKey, cats, caps];
            torznabProviders[id] = newData;

            $('#editATorznabProvider').append('<option value=' + id + '>' + name + '</option>');

            if ($('#provider_order_list > #' + id).length === 0) {
                $('#provider_order_list').append('<li class="ui-state-default" id="' + id + '"> <input type="checkbox" id="enable_' + id + '" class="provider_enabler" CHECKED> <a href="' + MEDUSA.config.anonURL + url + '" class="imgLink" target="_new"><img src="images/providers/jackett.png" alt="' + name + '" width="16" height="16"></a> ' + name + '</li>'); // eslint-disable-line no-undef
                $('#provider_order_list').sortable('refresh');
            }

            makeTorznabProviderString();
        };

        function updateNewznabProvider(id, url, apiKey, cats) {
            newznabProviders[id][1][1] = url;
            newznabProviders[id][1][2] = apiKey;
            newznabProviders[id][1][3] = cats;

            // Get Categories Capabilities
            if (id && url && apiKey) {
                const capabilities = getCategories('newznab', newznabProviders[id][1]);
                capabilities.done(function(data) {
                    if (data.categories) {
                        $('#newznab_cap').replaceOptions(data.categories);
                    }
                    makeNewznabProviderString();
                });
            }
        };

        function updateTorrentRssProvider(id, url, cookies, titleTag) {
            torrentRssProviders[id][1] = url;
            torrentRssProviders[id][2] = cookies;
            torrentRssProviders[id][3] = titleTag;
            populateTorrentRssSection();
            makeTorrentRssProviderString();
        };

        function updateTorznabProvider(id, url, apiKey, cats, caps) { // eslint-disable-line max-params
            torznabProviders[id][1] = url;
            torznabProviders[id][2] = apiKey;
            torznabProviders[id][3] = cats;
            torznabProviders[id][4] = caps;

            // Get Categories Capabilities
            if (id && url && apiKey) {
                const capabilities = getCategories('torznab', torznabProviders[id]);
                capabilities.done(function(data) {
                    if (data.categories) {
                        $('#torznab_cap').replaceOptions(data.categories);
                        if (data.params) {
                            torznabProviders[id][4] = data.params.toString();
                            $('#torznab_caps').val(data.params);
                        }
                    }
                    makeTorznabProviderString();
                });
            }
        };

        function deleteNewznabProvider(id) {
            $('#editANewznabProvider option[value=' + id + ']').remove();
            delete newznabProviders[id];
            populateNewznabSection();
            $('li').remove('#' + id);
            makeNewznabProviderString();
        };

        function deleteTorrentRssProvider(id) {
            $('#editATorrentRssProvider option[value=' + id + ']').remove();
            delete torrentRssProviders[id];
            populateTorrentRssSection();
            $('li').remove('#' + id);
            makeTorrentRssProviderString();
        };

        function deleteTorznabProvider(id) {
            $('#editATorznabProvider option[value=' + id + ']').remove();
            delete torznabProviders[id];
            populateTorznabSection();
            $('li').remove('#' + id);
            makeTorznabProviderString();
        };

        function populateNewznabSection() {
            const selectedProvider = $('#editANewznabProvider :selected').val();
            let data = '';
            let isDefault = '';
            let chosenCats = '';

            if (selectedProvider === 'addNewznab') {
                data = ['', '', ''];
                isDefault = 0;
                $('#newznab_add_div').show();
                $('#newznab_update_div').hide();
                $('#newznabcapdiv').hide();
                $('#newznab_cat option').each((index, element) => {
                    $(element).remove();
                });
            } else {
                data = newznabProviders[selectedProvider][1];
                isDefault = newznabProviders[selectedProvider][0];
                $('#newznab_add_div').hide();
                $('#newznab_update_div').show();
                $('#newznabcapdiv').show();
            }

            $('#newznab_name').val(data[0]);
            $('#newznab_url').val(data[1]);
            $('#newznab_api_key').val(data[2]);

            // Check if not already array
            if (typeof data[3] === 'string') {
                chosenCats = data[3].split(',');
            } else {
                chosenCats = data[3];
            }

            // Update the category select box (on the right)
            const newCatOptions = [];
            if (chosenCats) {
                chosenCats.forEach(cat => {
                    if (cat !== '') {
                        newCatOptions.push({
                            text: cat,
                            value: cat
                        });
                    }
                });
                $('#newznab_cat').replaceOptions(newCatOptions);
            }

            if (selectedProvider === 'addNewznab') {
                $('#newznab_name').prop('disabled', false);
                $('#newznab_url').prop('disabled', false);
            } else {
                $('#newznab_name').prop('disabled', true);

                if (isDefault) {
                    $('#newznab_url').prop('disabled', true);
                    $('#newznab_delete').prop('disabled', true);
                } else {
                    $('#newznab_url').prop('disabled', false);
                    $('#newznab_delete').prop('disabled', false);
                }
            }
        };

        function populateTorrentRssSection() {
            const selectedProvider = $('#editATorrentRssProvider :selected').val();
            let data = '';

            if (selectedProvider === 'addTorrentRss') {
                data = ['', '', '', 'title'];
                $('#torrentrss_add_div').show();
                $('#torrentrss_update_div').hide();
            } else {
                data = torrentRssProviders[selectedProvider];
                $('#torrentrss_add_div').hide();
                $('#torrentrss_update_div').show();
            }

            $('#torrentrss_name').val(data[0]);
            $('#torrentrss_url').val(data[1]);
            $('#torrentrss_cookies').val(data[2]);
            $('#torrentrss_title_tag').val(data[3]);

            if (selectedProvider === 'addTorrentRss') {
                $('#torrentrss_name').prop('disabled', false);
                $('#torrentrss_url').prop('disabled', false);
                $('#torrentrss_cookies').prop('disabled', false);
                $('#torrentrss_title_tag').prop('disabled', false);
            } else {
                $('#torrentrss_name').prop('disabled', true);
                $('#torrentrss_url').prop('disabled', false);
                $('#torrentrss_cookies').prop('disabled', true);
                $('#torrentrss_title_tag').prop('disabled', false);
                $('#torrentrss_delete').prop('disabled', false);
            }
        };

        function populateTorznabSection() {
            const selectedProvider = $('#editATorznabProvider :selected').val();
            let data = '';
            let chosenCats = '';

            if (selectedProvider === 'addTorznab') {
                data = ['', '', '', ''];
                $('#torznab_add_div').show();
                $('#torznab_update_div').hide();
                $('#torznabcapdiv').hide();
                $('#torznabcapsdiv').hide();
                $('#torznab_cat option').each((index, element) => {
                    $(element).remove();
                });
            } else {
                data = torznabProviders[selectedProvider];
                $('#torznab_add_div').hide();
                $('#torznab_update_div').show();
                $('#torznabcapdiv').show();
                $('#torznabcapsdiv').show();
            }

            $('#torznab_name').val(data[0]);
            $('#torznab_url').val(data[1]);
            $('#torznab_api_key').val(data[2]);
            $('#torznab_caps').val(data[4]);

            // Check if not already array
            if (typeof data[3] === 'string') {
                chosenCats = data[3].split(',');
            } else {
                chosenCats = data[3];
            }

            // Update the category select box (on the right)
            const newCatOptions = [];
            if (chosenCats) {
                chosenCats.forEach(cat => {
                    if (cat !== '') {
                        newCatOptions.push({
                            text: cat,
                            value: cat
                        });
                    }
                });
                $('#torznab_cat').replaceOptions(newCatOptions);
            }

            if (selectedProvider === 'addTorznab') {
                $('#torznab_name').prop('disabled', false);
                $('#torznab_url').prop('disabled', false);
            } else {
                $('#torznab_name').prop('disabled', true);
                $('#torznab_url').prop('disabled', false);
                $('#torznab_delete').prop('disabled', false);
            }
        };

        function makeNewznabProviderString() {
            const provStrings = [];

            for (const id in newznabProviders) {
                if ({}.hasOwnProperty.call(newznabProviders, id)) {
                    provStrings.push(newznabProviders[id][1].join('|'));
                }
            }

            $('#newznab_string').val(provStrings.join('!!!'));
        };

        function makeTorrentRssProviderString() {
            const provStrings = [];
            for (const id in torrentRssProviders) {
                if ({}.hasOwnProperty.call(torrentRssProviders, id)) {
                    provStrings.push(torrentRssProviders[id].join('|'));
                }
            }

            $('#torrentrss_string').val(provStrings.join('!!!'));
        };

        function makeTorznabProviderString() {
            const provStrings = [];

            for (const id in torznabProviders) {
                if ({}.hasOwnProperty.call(torznabProviders, id)) {
                    provStrings.push(torznabProviders[id].join('|'));
                }
            }

            $('#torznab_string').val(provStrings.join('!!!'));
        };

        function refreshProviderList() {
            const idArr = $('#provider_order_list').sortable('toArray');
            const finalArr = [];
            $.each(idArr, (key, val) => {
                const checked = $('#enable_' + val).is(':checked') ? '1' : '0';
                finalArr.push(val + ':' + checked);
            });

            $('#provider_order').val(finalArr.join(' '));
            refreshEditAProvider();
        };

        function refreshEditAProvider() {
            $('#provider-list').empty();

            const idArr = $('#provider_order_list').sortable('toArray');
            const finalArr = [];
            $.each(idArr, (key, val) => {
                if ($('#enable_' + val).prop('checked')) {
                    finalArr.push(val);
                }
            });

            if (finalArr.length > 0) {
                $('<select>').prop('id', 'editAProvider').addClass('form-control input-sm').appendTo('#provider-list');
                for (let i = 0, len = finalArr.length; i < len; i++) {
                    const provider = finalArr[i];
                    $('#editAProvider').append($('<option>').prop('value', provider).text($.trim($('#' + provider).text()).replace(/\s\*$/, '').replace(/\s\*\*$/, '')));
                }
            } else {
                document.getElementsByClassName('component-desc')[0].innerHTML = 'No providers available to configure.';
            }

            showHideProviders();
        };

        $(document.body).on('change', '.newznab_api_key', event => {
            let providerId = $(event.currentTarget).prop('id');
            providerId = providerId.substring(0, providerId.length - '_hash'.length);

            const url = $('#' + providerId + '_url').val();
            const cat = $('#' + providerId + '_cat').val();
            const key = $(event.currentTarget).val();

            updateNewznabProvider(providerId, url, key, cat);
        });

        $(document.body).on('change', '#newznab_api_key, #newznab_url', () => {
            const selectedProvider = $('#editANewznabProvider :selected').val();
            if (selectedProvider === 'addNewznab') {
                return;
            }

            const url = $('#newznab_url').val();
            const apiKey = $('#newznab_api_key').val();

            newznabProviders[selectedProvider][1][1] = url;
            newznabProviders[selectedProvider][1][2] = apiKey;

            makeNewznabProviderString();
        });

        $(document.body).on('change', '#torrentrss_url, #torrentrss_cookies, #torrentrss_title_tag', () => {
            const selectedProvider = $('#editATorrentRssProvider :selected').val();
            if (selectedProvider === 'addTorrentRss') {
                return;
            }

            const url = $('#torrentrss_url').val();
            const cookies = $('#torrentrss_cookies').val();
            const titleTag = $('#torrentrss_title_tag').val();

            updateTorrentRssProvider(selectedProvider, url, cookies, titleTag);
        });

        $(document.body).on('change', '#torznab_api_key, #torznab_url', event => {
            const selectedProvider = $('#editATorznabProvider :selected').val();
            if (selectedProvider === 'addTorznab') {
                return;
            }

            const url = $('#torznab_url').val();
            const apiKey = $('#torznab_api_key').val();

            torznabProviders[selectedProvider][1] = url;
            torznabProviders[selectedProvider][2] = apiKey;

            makeTorznabProviderString();
        });

        $(document.body).on('change', '#editAProvider', () => {
            showHideProviders();
        });

        $(document.body).on('change', '#editANewznabProvider', () => {
            $('#newznab_cap option').each((index, element) => {
                $(element).remove();
            });
            $('.updating_categories').empty();
            populateNewznabSection();
        });

        $(document.body).on('change', '#editATorrentRssProvider', () => {
            populateTorrentRssSection();
        });

        $(document.body).on('change', '#editATorznabProvider', () => {
            $('#torznab_cap option').each((index, element) => {
                $(element).remove();
            });
            $('.updating_categories').empty();
            populateTorznabSection();
        });

        $(document.body).on('click', '.provider_enabler', () => {
            refreshProviderList();
        });

        $(document.body).on('click', '#newznab_cat_update', () => {
            const selectedProvider = $('#editANewznabProvider :selected').val();

            const url = $('#newznab_url').val();
            const apiKey = $('#newznab_api_key').val();
            const cats = $('#newznab_cat option').map((i, opt) => {
                return $(opt).text();
            }).toArray().join(',');

            $('#newznab_cat option:not([value])').remove();

            updateNewznabProvider(selectedProvider, url, apiKey, cats);
        });

        $(document.body).on('click', '#torznab_cat_update', () => {
            const selectedProvider = $('#editATorznabProvider :selected').val();

            const url = $('#torznab_url').val();
            const apiKey = $('#torznab_api_key').val();
            const cats = $('#torznab_cat option').map((i, opt) => {
                return $(opt).text();
            }).toArray().join(',');
            const caps = $('#torznab_caps').val();

            $('#torznab_cat option:not([value])').remove();

            updateTorznabProvider(selectedProvider, url, apiKey, cats, caps);
        });

        $(document.body).on('click', '#newznab_cat_select', () => {
            const selectedProvider = $('#editANewznabProvider :selected').val();
            const newOptions = [];
            const newValues = [];
            // When the update botton is clicked, loop through the capabilities list
            // and copy the selected category id's to the category list on the right.
            $('#newznab_cap option:selected').each((index, element) => {
                const selectedCat = $(element).val();
                newOptions.push({
                    text: selectedCat,
                    value: selectedCat
                });
                newValues.push(selectedCat);
            });
            if (newOptions.length > 0) {
                $('#newznab_cat').replaceOptions(newOptions);
                const cats = newValues.join(',');
                newznabProviders[selectedProvider][1][3] = cats;
            }

            makeNewznabProviderString();
        });

        $(document.body).on('click', '#torznab_cat_select', () => {
            const selectedProvider = $('#editATorznabProvider :selected').val();
            const newOptions = [];
            const newValues = [];
            // When the update botton is clicked, loop through the capabilities list
            // and copy the selected category id's to the category list on the right.
            $('#torznab_cap option:selected').each((index, element) => {
                const selectedCat = $(element).val();
                newOptions.push({
                    text: selectedCat,
                    value: selectedCat
                });
                newValues.push(selectedCat);
            });
            if (newOptions.length > 0) {
                $('#torznab_cat').replaceOptions(newOptions);
                const cats = newValues.join(',');
                torznabProviders[selectedProvider][3] = cats;
            }

            makeTorznabProviderString();
        });

        $(document.body).on('click', '#newznab_add', () => {
            const name = $.trim($('#newznab_name').val());
            const url = $.trim($('#newznab_url').val());
            const apiKey = $.trim($('#newznab_api_key').val());

            const cats = $.trim($('#newznab_cat option').map((i, opt) => {
                return $(opt).text();
            }).toArray().join(','));

            if (!name || !url || !apiKey) {
                return;
            }

            const params = { kind: 'newznab', name, url };

            // Send to the form with ajax, get a return value
            $.getJSON('config/providers/canAddProvider', params, function(data) {
                if (data.error !== undefined) {
                    alert(data.error); // eslint-disable-line no-alert
                    return;
                }

                $('#newznabcapdiv').show();
                addNewznabProvider(data.success, name, url, apiKey, cats, 0);
                updateNewznabProvider(data.success, url, apiKey, cats);
                $('#editANewznabProvider').val(data.success);
            });
        });

        $(document.body).on('click', '#torrentrss_add', () => {
            const name = $('#torrentrss_name').val();
            const url = $('#torrentrss_url').val();
            const cookies = $('#torrentrss_cookies').val();
            const titleTag = $('#torrentrss_title_tag').val();
            const params = {
                name,
                url,
                cookies,
                title_tag: titleTag // eslint-disable-line camelcase
            };

            // @TODO: Move to the API
            // send to the form with ajax, get a return value
            $.getJSON('config/providers/canAddTorrentRssProvider', params, function(data) {
                if (data.error !== undefined) {
                    alert(data.error); // eslint-disable-line no-alert
                    return;
                }

                addTorrentRssProvider(data.success, name, url, cookies, titleTag);
                $('#editATorrentRssProvider').val(data.success);
            });
        });

        $(document.body).on('click', '#torznab_add', () => {
            const name = $.trim($('#torznab_name').val());
            const url = $.trim($('#torznab_url').val());
            const apiKey = $.trim($('#torznab_api_key').val());
            const caps = $.trim($('#torznab_caps').val());
            const cats = $.trim($('#torznab_cat option').map((i, opt) => {
                return $(opt).text();
            }).toArray().join(','));

            if (!name || !url || !apiKey) {
                return;
            }

            const params = { kind: 'torznab', name, url, api_key: apiKey }; // eslint-disable-line camelcase

            // Send to the form with ajax, get a return value
            $.getJSON('config/providers/canAddProvider', params, function(data) {
                if (data.error !== undefined) {
                    $('#torznabcapdiv').hide();
                    $('#torznabcapsdiv').hide();
                    alert(data.error); // eslint-disable-line no-alert
                    return;
                }

                $('#torznabcapdiv').show();
                $('#torznabcapsdiv').show();
                addTorznabProvider(data.success, name, url, apiKey, cats, caps);
                updateTorznabProvider(data.success, url, apiKey, cats, caps);
                $('#editATorznabProvider').val(data.success);
            });
        });

        $(document.body).on('click', '.newznab_delete', () => {
            const selectedProvider = $('#editANewznabProvider :selected').val();
            deleteNewznabProvider(selectedProvider);
        });

        $(document.body).on('click', '.torrentrss_delete', () => {
            const selectedProvider = $('#editATorrentRssProvider :selected').val();
            deleteTorrentRssProvider(selectedProvider);
        });

        $(document.body).on('click', '.torznab_delete', () => {
            const selectedProvider = $('#editATorznabProvider :selected').val();
            deleteTorznabProvider(selectedProvider);
        });

        $(document.body).on('change', '[class="providerDiv_tip"] input', event => {
            $('div .providerDiv [name=' + $(event.currentTarget).prop('name') + ']').replaceWith($(event.currentTarget).clone());
            $('div .providerDiv [newznab_name=' + $(event.currentTarget).prop('id') + ']').replaceWith($(event.currentTarget).clone());
        });

        $(document.body).on('change', '[class="providerDiv_tip"] select', event => {
            $(event.currentTarget).find('option').each((index, element) => {
                if ($(element).is(':selected')) {
                    $(element).prop('defaultSelected', true);
                } else {
                    $(element).prop('defaultSelected', false);
                }
            });
            $('div .providerDiv [name=' + $(event.currentTarget).prop('name') + ']').empty().replaceWith($(event.currentTarget).clone());
        });

        $(document.body).on('change', '.enabler', event => {
            if ($(event.currentTarget).is(':checked')) {
                $('.content_' + $(event.currentTarget).prop('id')).each((index, element) => {
                    $(element).show();
                });
            } else {
                $('.content_' + $(event.currentTarget).prop('id')).each((index, element) => {
                    $(element).hide();
                });
            }
        });

        $('.enabler').each((index, element) => {
            if ($(element).is(':checked')) {
                $('.content_' + $(element).prop('id')).show();
            } else {
                $('.content_' + $(element).prop('id')).hide();
            }
        });

        function makeTorrentOptionString(providerId) {
            const seedRatio = $('.providerDiv_tip #' + providerId + '_seed_ratio').prop('value');
            const seedTime = $('.providerDiv_tip #' + providerId + '_seed_time').prop('value');
            const processMet = $('.providerDiv_tip #' + providerId + '_process_method').prop('value');
            const optionString = $('.providerDiv_tip #' + providerId + '_option_string');

            optionString.val([seedRatio, seedTime, processMet].join('|'));
        };

        $(document.body).on('change', '.seed_option', event => {
            const providerId = $(event.currentTarget).prop('id').split('_')[0];
            makeTorrentOptionString(providerId);
        });

        $.fn.replaceOptions = function(options) {
            let $option;

            this.empty();
            const self = this;

            $.each(options, (index, option) => {
                $option = $('<option></option>').prop('value', option.value).text(option.text);
                self.append($option);
            });
        };

        // Initialization stuff
        const znabProvidersCapabilities = [];
        const newznabProviders = [];
        const torrentRssProviders = [];
        const torznabProviders = [];

        loadProviders();
        showHideProviders();

        $('#provider_order_list').sortable({
            placeholder: 'ui-state-highlight',
            update() {
                refreshProviderList();
            }
        });
    }
});
</script>
</%block>
<%block name="content">
<h1 class="header">{{ $route.meta.header }}</h1>
<div id="config">
    <div id="config-content">
        <form id="configForm" action="config/providers/saveProviders" method="post">
            <div id="config-components">
                <ul>
                    <li><app-link href="#provider-priorities">Provider Priorities</app-link></li>
                    <li><app-link href="#provider-options">Provider Options</app-link></li>
                  % if app.USE_NZBS:
                    <li><app-link href="#custom-newznab">Configure Custom Newznab Providers</app-link></li>
                  % endif
                  % if app.USE_TORRENTS:
                    <li><app-link href="#custom-torrent">Configure Custom Torrent Providers</app-link></li>
                    <li><app-link href="#custom-torznab">Configure Jackett Providers</app-link></li>
                  % endif
                </ul>
                <div id="provider-priorities" class="component-group" style='min-height: 550px;'>
                    <div class="component-group-desc-legacy">
                        <h3>Provider Priorities</h3>
                        <p>Check off and drag the providers into the order you want them to be used.</p>
                        <p>At least one provider is required but two are recommended.</p>
                        % if not app.USE_NZBS or not app.USE_TORRENTS:
                        <blockquote style="margin: 20px 0;">NZB/Torrent providers can be toggled in <b><app-link href="config/search">Search Settings</app-link></b></blockquote>
                        % else:
                        <br>
                        % endif
                        <div>
                            <p class="note"><span class="red-text">*</span> Provider does not support backlog searches at this time.</p>
                            <p class="note"><span class="red-text">!</span> Provider is <b>NOT WORKING</b>.</p>
                        </div>
                    </div>
                    <fieldset class="component-group-list">
                        <ul id="provider_order_list">
                        % for cur_provider in sorted_provider_list():
                            <%
                                ## These will show the '!' not saying they are broken
                                if cur_provider.provider_type == GenericProvider.NZB and not app.USE_NZBS:
                                    continue
                                elif cur_provider.provider_type == GenericProvider.TORRENT and not app.USE_TORRENTS:
                                    continue
                                curName = cur_provider.get_id()
                                if hasattr(cur_provider, 'custom_url'):
                                    curURL = cur_provider.custom_url or cur_provider.url
                                else:
                                    curURL = cur_provider.url
                            %>
                            <li class="ui-state-default ${('nzb-provider', 'torrent-provider')[bool(cur_provider.provider_type == GenericProvider.TORRENT)]}" id="${curName}">
                                <input type="checkbox" id="enable_${curName}" class="provider_enabler" ${'checked="checked"' if cur_provider.is_enabled() is True and cur_provider.get_id() not in app.BROKEN_PROVIDERS else ''}/>
                                <app-link href="${curURL}" class="imgLink" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;"><img src="images/providers/${cur_provider.image_name()}" alt="${cur_provider.name}" title="${cur_provider.name}" width="16" height="16" style="vertical-align:middle;"/></app-link>
                                <span style="vertical-align:middle;">${cur_provider.name}</span>
                                ${('<span class="red-text">*</span>', '')[bool(cur_provider.supports_backlog)]}
                                ${('<span class="red-text">!</span>', '')[bool(cur_provider.get_id() not in app.BROKEN_PROVIDERS)]}
                                <span class="ui-icon ui-icon-arrowthick-2-n-s pull-right" style="vertical-align:middle;" title="Re-order provider"></span>
                                <span class="ui-icon ${('ui-icon-locked','ui-icon-unlocked')[bool(cur_provider.public)]} pull-right" style="vertical-align:middle;" title="Public or Private"></span>
                                <span class="${('','ui-icon enable-manual-search-icon pull-right')[bool(cur_provider.enable_manualsearch)]}" style="vertical-align:middle;" title="Enabled for 'Manual Search' feature"></span>
                                <span class="${('','ui-icon enable-backlog-search-icon pull-right')[bool(cur_provider.enable_backlog)]}" style="vertical-align:middle;" title="Enabled for Backlog Searches"></span>
                                <span class="${('','ui-icon enable-daily-search-icon pull-right')[bool(cur_provider.enable_daily)]}" style="vertical-align:middle;" title="Enabled for Daily Searches"></span>
                            </li>
                        % endfor
                        </ul>
                        <input type="hidden" name="provider_order" id="provider_order" value="${" ".join([x.get_id()+':'+str(int(x.is_enabled())) for x in sorted_provider_list()])}"/>
                        <br><input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                    </fieldset>
                </div><!-- /component-group1 //-->
                <div id="provider-options" class="component-group">
                    <div class="component-group-desc-legacy">
                        <h3>Provider Options</h3>
                        <p>Configure individual provider settings here.</p>
                        <p>Check with provider's website on how to obtain an API key if needed.</p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="editAProvider" id="provider-list">
                                <span class="component-title">Configure provider:</span>
                                <span class="component-desc">
                                    <%
                                        provider_config_list = []
                                        for cur_provider in sorted_provider_list():
                                            if cur_provider.provider_type == GenericProvider.NZB and (not app.USE_NZBS or not cur_provider.is_enabled()):
                                                continue
                                            elif cur_provider.provider_type == GenericProvider.TORRENT and (not app.USE_TORRENTS or not cur_provider.is_enabled()):
                                                continue
                                            provider_config_list.append(cur_provider)
                                    %>
                                    % if provider_config_list:
                                        <select id="editAProvider" class="form-control input-sm">
                                            % for cur_provider in provider_config_list:
                                                <option value="${cur_provider.get_id()}">${cur_provider.name}</option>
                                            % endfor
                                        </select>
                                    % else:
                                        No providers available to configure.
                                    % endif
                                </span>
                            </label>
                        </div>
                    <!-- start div for editing providers //-->
                    % for cur_newznab_provider in [cur_provider for cur_provider in app.newznabProviderList]:
                    <div class="providerDiv" id="${cur_newznab_provider.get_id()}Div">
                        % if cur_newznab_provider.default and cur_newznab_provider.needs_auth:
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_url">
                                <span class="component-title">URL:</span>
                                <span class="component-desc">
                                    <input type="text" id="${cur_newznab_provider.get_id()}_url" value="${cur_newznab_provider.url}" class="form-control input-sm input350" disabled/>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_hash">
                                <span class="component-title">API key:</span>
                                <span class="component-desc">
                                    <input type="password" id="${cur_newznab_provider.get_id()}_hash" value="${cur_newznab_provider.api_key}" newznab_name="${cur_newznab_provider.get_id()}_hash" class="newznab_api_key form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'enable_daily'):
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_enable_daily">
                                <span class="component-title">Enable daily searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_newznab_provider.get_id()}_enable_daily" id="${cur_newznab_provider.get_id()}_enable_daily" ${'checked="checked"' if cur_newznab_provider.enable_daily else ''}/>
                                    <p>enable provider to perform daily searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'enable_manualsearch'):
                        <div class="field-pair${(' hidden', '')[cur_newznab_provider.supports_backlog]}">
                            <label for="${cur_newznab_provider.get_id()}_enable_manualsearch">
                                <span class="component-title">Enable for 'Manual search' feature</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_newznab_provider.get_id()}_enable_manualsearch" id="${cur_newznab_provider.get_id()}_enable_manualsearch" ${'checked="checked"' if cur_newznab_provider.enable_manualsearch  and cur_newznab_provider.supports_backlog else ''}/>
                                    <p>enable provider to be used in 'Manual Search' feature.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'enable_backlog'):
                        <div class="field-pair${(' hidden', '')[cur_newznab_provider.supports_backlog]}">
                            <label for="${cur_newznab_provider.get_id()}_enable_backlog">
                                <span class="component-title">Enable backlog searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_newznab_provider.get_id()}_enable_backlog" id="${cur_newznab_provider.get_id()}_enable_backlog" ${'checked="checked"' if cur_newznab_provider.enable_backlog and cur_newznab_provider.supports_backlog else ''}/>
                                    <p>enable provider to perform backlog searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'search_mode'):
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Backlog search mode</span>
                                <span class="component-desc">
                                    <p>when searching with backlog you can choose to have it look for season packs only, or choose to have it build a complete season from just single episodes.</p>
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_newznab_provider.get_id()}_search_mode" id="${cur_newznab_provider.get_id()}_search_mode_sponly" value="sponly" ${'checked="checked"' if cur_newznab_provider.search_mode=="sponly" else ''}/>season packs only.
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_newznab_provider.get_id()}_search_mode" id="${cur_newznab_provider.get_id()}_search_mode_eponly" value="eponly" ${'checked="checked"' if cur_newznab_provider.search_mode=="eponly" else ''}/>episodes only.
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'search_fallback'):
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_search_fallback">
                                <span class="component-title">Enable fallback</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_newznab_provider.get_id()}_search_fallback" id="${cur_newznab_provider.get_id()}_search_fallback" ${'checked="checked"' if cur_newznab_provider.search_fallback else ''}/>
                                    <p>when searching for a complete season depending on search mode you may return no results, this helps by restarting the search using the opposite search mode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'enable_search_delay'):
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_enable_search_delay">
                                <span class="component-title">Enable search delay</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_newznab_provider.get_id()}_enable_search_delay" id="${cur_newznab_provider.get_id()}_enable_search_delay" ${'checked="checked"' if cur_newznab_provider.enable_search_delay else ''}/>
                                    <p>Enable to delay downloads for this provider for an x amount of hours. The provider will start snatching results for a specific episode after a delay has expired, compared to when it first got a result for the specific episode.</p>
                                    <p>Searches for PROPER releases are exempted from the delay.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'search_delay'):
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_ratio">
                                <span class="component-title" id="${cur_newznab_provider.get_id()}_search_delay">Search delay (hours):</span>
                                <span class="component-desc">
                                    <input type="number" min="0.5" step="0.5" name="${cur_newznab_provider.get_id()}_search_delay" id="${cur_newznab_provider.get_id()}_search_delay" value="${8 if cur_newznab_provider.search_delay is None else round(cur_newznab_provider.search_delay / 60.0, 1)}" class="form-control input-sm input75" />
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    <p>Amount of hours to wait for downloading a result compared to the first result for a specific episode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                    </div>
                    % endfor
                    % for cur_nzb_provider in [cur_provider for cur_provider in sorted_provider_list() if cur_provider.provider_type == GenericProvider.NZB and cur_provider not in app.newznabProviderList]:
                    <div class="providerDiv" id="${cur_nzb_provider.get_id()}Div">
                        % if hasattr(cur_nzb_provider, 'username'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_username">
                                <span class="component-title">Username:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_nzb_provider.get_id()}_username" value="${cur_nzb_provider.username}" class="form-control input-sm input350"
                                           autocomplete="no" />
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'api_key'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_api_key">
                                <span class="component-title">API key:</span>
                                <span class="component-desc">
                                    <input type="password" name="${cur_nzb_provider.get_id()}_api_key" value="${cur_nzb_provider.api_key}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'enable_daily'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_enable_daily">
                                <span class="component-title">Enable daily searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_nzb_provider.get_id()}_enable_daily" id="${cur_nzb_provider.get_id()}_enable_daily" ${'checked="checked"' if cur_nzb_provider.enable_daily else ''}/>
                                    <p>enable provider to perform daily searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'enable_manualsearch'):
                        <div class="field-pair${(' hidden', '')[cur_nzb_provider.supports_backlog]}">
                            <label for="${cur_nzb_provider.get_id()}_enable_manualsearch">
                                <span class="component-title">Enable 'Manual Search' feature</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_nzb_provider.get_id()}_enable_manualsearch" id="${cur_nzb_provider.get_id()}_enable_manualsearch" ${'checked="checked"' if cur_nzb_provider.enable_manualsearch and cur_nzb_provider.supports_backlog else ''}/>
                                     <p>enable provider to be used in 'Manual Search' feature.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'enable_backlog'):
                        <div class="field-pair${(' hidden', '')[cur_nzb_provider.supports_backlog]}">
                            <label for="${cur_nzb_provider.get_id()}_enable_backlog">
                                <span class="component-title">Enable backlog searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_nzb_provider.get_id()}_enable_backlog" id="${cur_nzb_provider.get_id()}_enable_backlog" ${'checked="checked"' if cur_nzb_provider.enable_backlog and cur_nzb_provider.supports_backlog else ''}/>
                                    <p>enable provider to perform backlog searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'search_mode'):
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Backlog search mode</span>
                                <span class="component-desc">
                                    <p>when searching with backlog you can choose to have it look for season packs only, or choose to have it build a complete season from just single episodes.</p>
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_nzb_provider.get_id()}_search_mode" id="${cur_nzb_provider.get_id()}_search_mode_sponly" value="sponly" ${'checked="checked"' if cur_nzb_provider.search_mode=="sponly" else ''}/>season packs only.
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_nzb_provider.get_id()}_search_mode" id="${cur_nzb_provider.get_id()}_search_mode_eponly" value="eponly" ${'checked="checked"' if cur_nzb_provider.search_mode=="eponly" else ''}/>episodes only.
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'search_fallback'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_search_fallback">
                                <span class="component-title">Enable fallback</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_nzb_provider.get_id()}_search_fallback" id="${cur_nzb_provider.get_id()}_search_fallback" ${'checked="checked"' if cur_nzb_provider.search_fallback else ''}/>
                                    <p>when searching for a complete season depending on search mode you may return no results, this helps by restarting the search using the opposite search mode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'enable_search_delay'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_enable_search_delay">
                                <span class="component-title">Enable search delay</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_nzb_provider.get_id()}_enable_search_delay" id="${cur_nzb_provider.get_id()}_enable_search_delay" ${'checked="checked"' if cur_nzb_provider.enable_search_delay else ''}/>
                                    <p>Enable to delay downloads for this provider for an x amount of hours. The provider will start snatching results for a specific episode after a delay has expired, compared to when it first got a result for the specific episode.</p>
                                    <p>Searches for PROPER releases are exempted from the delay.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'search_delay'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_ratio">
                                <span class="component-title" id="${cur_nzb_provider.get_id()}_search_delay">Search delay (hours):</span>
                                <span class="component-desc">
                                    <input type="number" min="0.5" step="0.5" name="${cur_nzb_provider.get_id()}_search_delay" id="${cur_nzb_provider.get_id()}_search_delay" value="${8 if cur_nzb_provider.search_delay is None else round(cur_nzb_provider.search_delay / 60.0, 1)}" class="form-control input-sm input75" />
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    <p>Amount of hours to wait for downloading a result compared to the first result for a specific episode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                    </div>
                    % endfor
                    % for cur_torrent_provider in [cur_provider for cur_provider in sorted_provider_list() if cur_provider.provider_type == GenericProvider.TORRENT]:
                    <div class="providerDiv" id="${cur_torrent_provider.get_id()}Div">
                        % if hasattr(cur_torrent_provider, 'custom_url'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_custom_url">
                                <span class="component-title">Custom URL:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_custom_url" id="${cur_torrent_provider.get_id()}_custom_url" value="${cur_torrent_provider.custom_url}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    <p>The URL should include the protocol (and port if applicable).  Examples:  http://192.168.1.4/ or http://localhost:3000/</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'api_key') and not isinstance(cur_torrent_provider, TorznabProvider):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_api_key">
                                <span class="component-title">Api key:</span>
                                <span class="component-desc">
                                    <input type="password" name="${cur_torrent_provider.get_id()}_api_key" id="${cur_torrent_provider.get_id()}_api_key" value="${cur_torrent_provider.api_key}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'digest'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_digest">
                                <span class="component-title">Digest:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_digest" id="${cur_torrent_provider.get_id()}_digest" value="${cur_torrent_provider.digest}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'hash'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_hash">
                                <span class="component-title">Hash:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_hash" id="${cur_torrent_provider.get_id()}_hash" value="${cur_torrent_provider.hash}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'username'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_username">
                                <span class="component-title">Username:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_username" id="${cur_torrent_provider.get_id()}_username" value="${cur_torrent_provider.username}" class="form-control input-sm input350"
                                           autocomplete="no" />
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'password'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_password">
                                <span class="component-title">Password:</span>
                                <span class="component-desc">
                                    <input type="password" name="${cur_torrent_provider.get_id()}_password" id="${cur_torrent_provider.get_id()}_password" value="${cur_torrent_provider.password | h}" class="form-control input-sm input350" autocomplete="no"/>
                                </span>
                            </label>
                        </div>
                        % endif

                        % if cur_torrent_provider.enable_cookies or cur_torrent_provider in app.torrentRssProviderList:
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_cookies">
                                <span class="component-title">Cookies:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_cookies" id="${cur_torrent_provider.get_id()}_cookies" value="${cur_torrent_provider.cookies}" class="form-control input-sm input350" autocapitalize="off" autocomplete="no" />
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    % if hasattr(cur_torrent_provider, 'required_cookies'):
                                        <p>eg. ${'=xx;'.join(cur_torrent_provider.required_cookies) + '=xx'}</p>
                                        <p>This provider requires the following cookies: ${', '.join(cur_torrent_provider.required_cookies)}. <br/>For a step by step guide please follow the link to our <app-link href="https://github.com/pymedusa/Medusa/wiki/Configure-Providers-with-captcha-protection">WIKI</app-link></p>
                                    % endif
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'passkey'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_passkey">
                                <span class="component-title">Passkey:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_passkey" id="${cur_torrent_provider.get_id()}_passkey" value="${cur_torrent_provider.passkey}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'pin'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_pin">
                                <span class="component-title">Pin:</span>
                                <span class="component-desc">
                                    <input type="password" name="${cur_torrent_provider.get_id()}_pin" id="${cur_torrent_provider.get_id()}_pin" value="${cur_torrent_provider.pin}" class="form-control input-sm input100" autocomplete="no"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'ratio'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_ratio">
                                <span class="component-title" id="${cur_torrent_provider.get_id()}_ratio_desc">Seed ratio:</span>
                                <span class="component-desc">
                                    <input type="number" min="-1" step="0.1" name="${cur_torrent_provider.get_id()}_ratio" id="${cur_torrent_provider.get_id()}_ratio" value="${cur_torrent_provider.ratio}" class="form-control input-sm input75" />
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    <p>stop transfer when ratio is reached<br>(-1 Medusa default to seed forever, or leave blank for downloader default)</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'minseed'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_minseed">
                                <span class="component-title" id="${cur_torrent_provider.get_id()}_minseed_desc">Minimum seeders:</span>
                                <span class="component-desc">
                                    <input type="number" min="0" step="1" name="${cur_torrent_provider.get_id()}_minseed" id="${cur_torrent_provider.get_id()}_minseed" value="${cur_torrent_provider.minseed}" class="form-control input-sm input75" />
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'minleech'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_minleech">
                                <span class="component-title" id="${cur_torrent_provider.get_id()}_minleech_desc">Minimum leechers:</span>
                                <span class="component-desc">
                                    <input type="number" min="0" step="1" name="${cur_torrent_provider.get_id()}_minleech" id="${cur_torrent_provider.get_id()}_minleech" value="${cur_torrent_provider.minleech}" class="form-control input-sm input75" />
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'confirmed'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_confirmed">
                                <span class="component-title">Confirmed download</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_confirmed" id="${cur_torrent_provider.get_id()}_confirmed" ${'checked="checked"' if cur_torrent_provider.confirmed else ''}/>
                                    <p>only download torrents from trusted or verified uploaders ?</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'ranked'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_ranked">
                                <span class="component-title">Ranked torrents</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_ranked" id="${cur_torrent_provider.get_id()}_ranked" ${'checked="checked"' if cur_torrent_provider.ranked else ''} />
                                    <p>only download ranked torrents (trusted releases)</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'engrelease'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_engrelease">
                                <span class="component-title">English torrents</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_engrelease" id="${cur_torrent_provider.get_id()}_engrelease" ${'checked="checked"' if cur_torrent_provider.engrelease else ''} />
                                    <p>only download english torrents, or torrents containing english subtitles</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'onlyspasearch'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_onlyspasearch">
                                <span class="component-title">For Spanish torrents</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_onlyspasearch" id="${cur_torrent_provider.get_id()}_onlyspasearch" ${'checked="checked"' if cur_torrent_provider.onlyspasearch else ''} />
                                    <p>ONLY search on this provider if show info is defined as "Spanish" (avoid provider's use for VOS shows)</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'sorting'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_sorting">
                                <span class="component-title">Sorting results by</span>
                                <span class="component-desc">
                                    <select name="${cur_torrent_provider.get_id()}_sorting" id="${cur_torrent_provider.get_id()}_sorting" class="form-control input-sm">
                                    % for cur_action in ('last', 'seeders', 'leechers'):
                                    <option value="${cur_action}" ${'selected="selected"' if cur_action == cur_torrent_provider.sorting else ''}>${cur_action}</option>
                                    % endfor
                                    </select>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'freeleech'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_freeleech">
                                <span class="component-title">Freeleech</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_freeleech" id="${cur_torrent_provider.get_id()}_freeleech" ${'checked="checked"' if cur_torrent_provider.freeleech else ''}/>
                                    <p>only download <b>"FreeLeech"</b> torrents.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'enable_daily'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_enable_daily">
                                <span class="component-title">Enable daily searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_enable_daily" id="${cur_torrent_provider.get_id()}_enable_daily" ${'checked="checked"' if cur_torrent_provider.enable_daily else ''}/>
                                    <p>enable provider to perform daily searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'enable_manualsearch'):
                        <div class="field-pair${(' hidden', '')[cur_torrent_provider.supports_backlog]}">
                            <label for="${cur_torrent_provider.get_id()}_enable_manualsearch">
                                <span class="component-title">Enable 'Manual Search' feature</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_enable_manualsearch" id="${cur_torrent_provider.get_id()}_enable_manualsearch" ${'checked="checked"' if cur_torrent_provider.enable_manualsearch and cur_torrent_provider.supports_backlog else ''}/>
                                    <p>enable provider to be used in 'Manual Search' feature.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'enable_backlog'):
                        <div class="field-pair${(' hidden', '')[cur_torrent_provider.supports_backlog]}">
                            <label for="${cur_torrent_provider.get_id()}_enable_backlog">
                                <span class="component-title">Enable backlog searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_enable_backlog" id="${cur_torrent_provider.get_id()}_enable_backlog" ${'checked="checked"' if cur_torrent_provider.enable_backlog and cur_torrent_provider.supports_backlog else ''}/>
                                    <p>enable provider to perform backlog searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'search_mode'):
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Backlog search mode</span>
                                <span class="component-desc">
                                    <p>when searching with backlog you can choose to have it look for season packs only, or choose to have it build a complete season from just single episodes.</p>
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_torrent_provider.get_id()}_search_mode" id="${cur_torrent_provider.get_id()}_search_mode_sponly" value="sponly" ${'checked="checked"' if cur_torrent_provider.search_mode=="sponly" else ''}/>season packs only.
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_torrent_provider.get_id()}_search_mode" id="${cur_torrent_provider.get_id()}_search_mode_eponly" value="eponly" ${'checked="checked"' if cur_torrent_provider.search_mode=="eponly" else ''}/>episodes only.
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'search_fallback'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_search_fallback">
                                <span class="component-title">Enable fallback</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_search_fallback" id="${cur_torrent_provider.get_id()}_search_fallback" ${'checked="checked"' if cur_torrent_provider.search_fallback else ''}/>
                                    <p>when searching for a complete season depending on search mode you may return no results, this helps by restarting the search using the opposite search mode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'cat') and cur_torrent_provider.get_id() == 'tntvillage':
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_cat">
                                <span class="component-title">Category:</span>
                                <span class="component-desc">
                                    <select name="${cur_torrent_provider.get_id()}_cat" id="${cur_torrent_provider.get_id()}_cat" class="form-control input-sm">
                                        % for i in cur_torrent_provider.category_dict.keys():
                                        <option value="${cur_torrent_provider.category_dict[i]}" ${('', 'selected="selected"')[cur_torrent_provider.category_dict[i] == cur_torrent_provider.cat]}>${i}</option>
                                        % endfor
                                    </select>
                                </span>
                           </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'subtitle') and cur_torrent_provider.get_id() == 'tntvillage':
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_subtitle">
                                <span class="component-title">Subtitled</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_subtitle" id="${cur_torrent_provider.get_id()}_subtitle" ${'checked="checked"' if cur_torrent_provider.subtitle else ''}/>
                                    <p>select torrent with Italian subtitle</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'enable_search_delay'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_enable_search_delay">
                                <span class="component-title">Enable search delay</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_enable_search_delay" id="${cur_torrent_provider.get_id()}_enable_search_delay" ${'checked="checked"' if cur_torrent_provider.enable_search_delay else ''}/>
                                    <p>Enable to delay downloads for this provider for an x amount of hours. The provider will start snatching results for a specific episode after a delay has expired, compared to when it first got a result for the specific episode.</p>
                                    <p>Searches for PROPER releases are exempted from the delay.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'search_delay'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_ratio">
                                <span class="component-title" id="${cur_torrent_provider.get_id()}_search_delay">Search delay (hours):</span>
                                <span class="component-desc">
                                    <input type="number" min="0.5" step="0.5" name="${cur_torrent_provider.get_id()}_search_delay" id="${cur_torrent_provider.get_id()}_search_delay" value="${8 if cur_torrent_provider.search_delay is None else round(cur_torrent_provider.search_delay / 60.0, 1)}" class="form-control input-sm input75" />
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    <p>Amount of hours to wait for downloading a result compared to the first result for a specific episode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                    </div>
                    % endfor
                    <!-- end div for editing providers -->
                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                    </fieldset>
                </div><!-- /component-group2 //-->
                % if app.USE_NZBS:
                <div id="custom-newznab" class="component-group">
                    <div class="component-group-desc-legacy">
                        <h3>Configure Custom Newznab Providers</h3>
                        <p>Add and setup or remove custom Newznab providers.</p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="newznab_string">
                                <span class="component-title">Select provider:</span>
                                <span class="component-desc">
                                    <input type="hidden" name="newznab_string" id="newznab_string" />
                                    <select id="editANewznabProvider" class="form-control input-sm">
                                        <option value="addNewznab">-- add new provider --</option>
                                    </select>
                                </span>
                            </label>
                        </div>
                        <div class="newznabProviderDiv" id="addNewznab">
                            <div class="field-pair">
                                <label for="newznab_name">
                                    <span class="component-title">Provider name:</span>
                                    <input type="text" id="newznab_name" class="form-control input-sm input200"/>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="newznab_url">
                                    <span class="component-title">Site URL:</span>
                                    <input type="text" id="newznab_url" class="form-control input-sm input350"/>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="newznab_api_key">
                                    <span class="component-title">API key:</span>
                                    <input type="password" id="newznab_api_key" class="form-control input-sm input350"/>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">Type <b>0</b>, if not required.</span>
                                </label>
                            </div>
                            <div class="field-pair" id="newznabcapdiv" style="display: none;">
                                <label>
                                    <span class="component-title">Newznab search categories:</span>
                                    <select id="newznab_cap" multiple="multiple" style="min-width:10em;" ></select>
                                    <select id="newznab_cat" multiple="multiple" style="min-width:10em;" ></select>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">Select your Newznab categories on the left, and click the "select categories" button to use them for searching. <b>Don't forget to to save the form!</b></span>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">
                                        <input class="btn-medusa" type="button" class="newznab_cat_update" id="newznab_cat_update" value="Update Categories" />
                                        <input class="btn-medusa" type="button" class="newznab_cat_select" id="newznab_cat_select" value="Select Categories" />
                                        <span class="updating_categories"></span>
                                    </span>
                                </label>
                            </div>
                            <div id="newznab_add_div">
                                <input class="btn-medusa" type="button" class="newznab_save" id="newznab_add" value="Add" />
                            </div>
                            <div id="newznab_update_div" style="display: none;">
                                <input class="btn-medusa btn-danger newznab_delete" type="button" class="newznab_delete" id="newznab_delete" value="Delete" />
                            </div>
                        </div>
                    </fieldset>
                </div><!-- /component-group3 //-->
                % endif
                % if app.USE_TORRENTS:
                <div id="custom-torrent" class="component-group">
                    <div class="component-group-desc-legacy">
                        <h3>Configure Custom Torrent Providers</h3>
                        <p>Add and setup or remove custom RSS providers.</p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="torrentrss_string">
                                <span class="component-title">Select provider:</span>
                                <span class="component-desc">
                                <input type="hidden" name="torrentrss_string" id="torrentrss_string" />
                                    <select id="editATorrentRssProvider" class="form-control input-sm">
                                        <option value="addTorrentRss">-- add new provider --</option>
                                    </select>
                                </span>
                            </label>
                        </div>
                        <div class="torrentRssProviderDiv" id="addTorrentRss">
                            <div class="field-pair">
                                <label for="torrentrss_name">
                                    <span class="component-title">Provider name:</span>
                                    <input type="text" id="torrentrss_name" class="form-control input-sm input200"/>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="torrentrss_url">
                                    <span class="component-title">RSS URL:</span>
                                    <input type="text" id="torrentrss_url" class="form-control input-sm input350"/>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="torrentrss_cookies">
                                    <span class="component-title">Cookies (optional):</span>
                                    <input type="text" id="torrentrss_cookies" class="form-control input-sm input350" />
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">eg. uid=xx;pass=yy, please use "Provider options" to reconfigure!</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="torrentrss_title_tag">
                                    <span class="component-title">Search element:</span>
                                    <input type="text" id="torrentrss_title_tag" class="form-control input-sm input200" value="title"/>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">eg: title</span>
                                </label>
                            </div>
                            <div id="torrentrss_add_div">
                                <input type="button" class="btn-medusa torrentrss_save" id="torrentrss_add" value="Add" />
                            </div>
                            <div id="torrentrss_update_div" style="display: none;">
                                <input type="button" class="btn-medusa btn-danger torrentrss_delete" id="torrentrss_delete" value="Delete" />
                            </div>
                        </div>
                    </fieldset>
                </div><!-- /component-group4 //-->
                <div id="custom-torznab" class="component-group">
                    <div class="component-group-desc-legacy">
                        <h3>Configure Jackett Providers</h3>
                        <p>Add and setup or remove Jackett providers.</p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="torznab_string">
                                <span class="component-title">Select provider:</span>
                                <span class="component-desc">
                                    <input type="hidden" name="torznab_string" id="torznab_string" />
                                    <select id="editATorznabProvider" class="form-control input-sm">
                                        <option value="addTorznab">-- add new provider --</option>
                                    </select>
                                </span>
                            </label>
                        </div>
                        <div class="torznabProviderDiv" id="addTorznab">
                            <div class="field-pair">
                                <label for="torznab_name">
                                    <span class="component-title">Provider name:</span>
                                    <input type="text" id="torznab_name" class="form-control input-sm input200"/>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="torznab_url">
                                    <span class="component-title">Site URL:</span>
                                    <input type="text" id="torznab_url" class="form-control input-sm input350"/>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="torznab_api_key">
                                    <span class="component-title">API key:</span>
                                    <input type="password" id="torznab_api_key" class="form-control input-sm input350"/>
                                </label>
                            </div>
                            <div class="field-pair" id="torznabcapsdiv" style="display: none;">
                                <label for="torznab_caps">
                                    <span class="component-title">Supported params:</span>
                                    <input type="text" id="torznab_caps" class="form-control input-sm input350" disabled/>
                                </label>
                            </div>
                            <div class="field-pair" id="torznabcapdiv" style="display: none;">
                                <label>
                                    <span class="component-title">Torznab search categories:</span>
                                    <select id="torznab_cap" multiple="multiple" style="min-width:10em;" ></select>
                                    <select id="torznab_cat" multiple="multiple" style="min-width:10em;" ></select>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">Select your Torznab categories on the left, and click the "select categories" button to use them for searching. <b>Don't forget to to save the form!</b></span>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">
                                        <input class="btn-medusa" type="button" class="torznab_cat_update" id="torznab_cat_update" value="Update Categories" />
                                        <input class="btn-medusa" type="button" class="torznab_cat_select" id="torznab_cat_select" value="Select Categories" />
                                        <span class="updating_categories"></span>
                                    </span>
                                </label>
                            </div>
                            <div id="torznab_add_div">
                                <input class="btn-medusa" type="button" class="torznab_save" id="torznab_add" value="Add" />
                            </div>
                            <div id="torznab_update_div" style="display: none;">
                                <input class="btn-medusa btn-danger torznab_delete" type="button" class="torznab_delete" id="torznab_delete" value="Delete" />
                            </div>
                        </div>
                    </fieldset>
                </div><!-- /component-group5 //-->
                % endif
                <br><input type="submit" class="btn-medusa config_submitter_refresh" value="Save Changes" /><br>
            </div><!-- /config-components //-->
        </form>
    </div>
</div>
</%block>
