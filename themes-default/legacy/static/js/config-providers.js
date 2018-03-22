$(document).ready(function() { // eslint-disable-line max-lines
    console.log('This function need to be moved to config/providers.js but can\'t be as we\'ve got scope issues currently.');
    $.fn.showHideProviders = function() {
        $('.providerDiv').each(function() {
            var providerName = $(this).prop('id');
            var selectedProvider = $('#editAProvider :selected').val();

            if (selectedProvider + 'Div' === providerName) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    };

    $.fn.providerExists = function(providerList, searchFor) {
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
    $.fn.getCategories = function(selectedProvider) {
        var name = selectedProvider[0];
        var url = selectedProvider[1];
        var apiKey = selectedProvider[2];

        if (!name || !url || !apiKey) {
            return;
        }

        $('.updating_categories').wrapInner('<span><img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif"> Updating Categories...</span>');

        const dfd = new $.Deferred();
        let capabilities = [];

        if ($(this).providerExists($.fn.newznabProvidersCapabilities, name)) {
            $('.updating_categories').empty();
            $('.updating_categories').wrapInner('<span>Categories updated!</span>');
            capabilities = $(this).updateCategories([], name);
            dfd.resolve(capabilities);
        } else {
            const params = { url, name, api_key: apiKey }; // eslint-disable-line camelcase
            const jqxhr = $.getJSON('config/providers/getNewznabCategories', params);
            jqxhr.always(function(data) {
                $('.updating_categories').empty();
                if (data.success === true) {
                    $('.updating_categories').wrapInner('<span>Categories updated!</span>');
                    capabilities = $(this).updateCategories(data, name);
                } else {
                    $('.updating_categories').wrapInner('<span>Updating categories failed!</span>');
                }
                dfd.resolve(capabilities);
            });
        }

        return dfd.promise();
    };

    /**
     * Updates the Global array $.fn.newznabProvidersCapabilities with a combination of newznab prov name
     * and category capabilities. Return
     * @param {Array} newzNabCaps, is the returned object with newznabprovider Name and Capabilities.
     * @param {Array} providerName
     * @return no return data. The multiselect input $("#newznab_cap") is updated, as a result.
     */
    $.fn.updateCategories = function(newzNabCaps, providerName) {
        if (newzNabCaps && !$(this).providerExists($.fn.newznabProvidersCapabilities, providerName)) {
            $.fn.newznabProvidersCapabilities.push({
                name: providerName,
                categories: newzNabCaps.tv_categories, // eslint-disable-line camelcase
                params: newzNabCaps.caps
            });
        }

        // Loop through the array and if currently selected newznab provider name matches one in the array, use it to
        // update the capabilities select box (on the left).
        const newCapOptions = [];
        let providerParams = '';
        if (providerName) {
            $.fn.newznabProvidersCapabilities.forEach(function(newzNabCap) {
                if (newzNabCap.name && newzNabCap.name === providerName && Array.isArray(newzNabCap.categories)) {
                    providerParams = newzNabCap.params;
                    newzNabCap.categories.forEach(function(categorySet) {
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
        if (!url) {
            alert('Invalid URL specified!'); // eslint-disable-line no-alert
            return;
        }

        if (!/^https?:\/\//i.test(url)) {
            url = 'http://' + url;
        }

        if (trailingSlash && url.match('/$') === null) {
            url += '/';
        }

        return url;
    }

    var newznabProviders = [];
    var torrentRssProviders = [];
    var torznabProviders = [];

    $.fn.addNewznabProvider = function(id, name, url, apiKey, cats, isDefault) { // eslint-disable-line max-params
        var verifiedUrl = verifyUrl(url);
        var newData = [isDefault, [name, verifiedUrl, apiKey, cats]];
        newznabProviders[id] = newData;

        $('#editANewznabProvider').append('<option value=' + id + '>' + name + '</option>');

        if ($('#provider_order_list > #' + id).length === 0) {
            $('#provider_order_list').append('<li class="ui-state-default" id="' + id + '"> <input type="checkbox" id="enable_' + id + '" class="provider_enabler" CHECKED> <a href="' + MEDUSA.config.anonURL + url + '" class="imgLink" target="_new"><img src="images/providers/newznab.png" alt="' + name + '" width="16" height="16"></a> ' + name + '</li>'); // eslint-disable-line no-undef
            $('#provider_order_list').sortable('refresh');
        }

        $(this).makeNewznabProviderString();
    };

    $.fn.addTorrentRssProvider = function(id, name, url, cookies, titleTag) { // eslint-disable-line max-params
        var verifiedUrl = verifyUrl(url, false);
        var newData = [name, verifiedUrl, cookies, titleTag];
        torrentRssProviders[id] = newData;

        $('#editATorrentRssProvider').append('<option value=' + id + '>' + name + '</option>');

        if ($('#provider_order_list > #' + id).length === 0) {
            $('#provider_order_list').append('<li class="ui-state-default" id="' + id + '"> <input type="checkbox" id="enable_' + id + '" class="provider_enabler" CHECKED> <a href="' + MEDUSA.config.anonURL + url + '" class="imgLink" target="_new"><img src="images/providers/torrentrss.png" alt="' + name + '" width="16" height="16"></a> ' + name + '</li>'); // eslint-disable-line no-undef
            $('#provider_order_list').sortable('refresh');
        }

        $(this).makeTorrentRssProviderString();
    };

    $.fn.addTorznabProvider = function(id, name, url, apiKey, cats, caps) { // eslint-disable-line max-params
        var verifiedUrl = verifyUrl(url);
        var newData = [name, verifiedUrl, apiKey, cats, caps];
        torznabProviders[id] = newData;

        $('#editATorznabProvider').append('<option value=' + id + '>' + name + '</option>');

        if ($('#provider_order_list > #' + id).length === 0) {
            $('#provider_order_list').append('<li class="ui-state-default" id="' + id + '"> <input type="checkbox" id="enable_' + id + '" class="provider_enabler" CHECKED> <a href="' + MEDUSA.config.anonURL + url + '" class="imgLink" target="_new"><img src="images/providers/jackett.png" alt="' + name + '" width="16" height="16"></a> ' + name + '</li>'); // eslint-disable-line no-undef
            $('#provider_order_list').sortable('refresh');
        }

        $(this).makeTorznabProviderString();
    };

    $.fn.updateNewznabProvider = function(id, url, apiKey, cats) {
        newznabProviders[id][1][1] = url;
        newznabProviders[id][1][2] = apiKey;
        newznabProviders[id][1][3] = cats;

        // Get Categories Capabilities
        if (id && url && apiKey) {
            const capabilities = $(this).getCategories(newznabProviders[id][1]);
            capabilities.done(function(data) {
                if (data.categories) {
                    $('#newznab_cap').replaceOptions(data.categories);
                }
                $(this).makeNewznabProviderString();
            });
        }
    };

    $.fn.updateTorrentRssProvider = function(id, url, cookies, titleTag) {
        torrentRssProviders[id][1] = url;
        torrentRssProviders[id][2] = cookies;
        torrentRssProviders[id][3] = titleTag;
        $(this).populateTorrentRssSection();
        $(this).makeTorrentRssProviderString();
    };

    $.fn.updateTorznabProvider = function(id, url, apiKey, cats, caps) { // eslint-disable-line max-params
        torznabProviders[id][1] = url;
        torznabProviders[id][2] = apiKey;
        torznabProviders[id][3] = cats;
        torznabProviders[id][4] = caps;

        // Get Categories Capabilities
        if (id && url && apiKey) {
            const capabilities = $(this).getCategories(torznabProviders[id]);
            capabilities.done(function(data) {
                if (data.categories) {
                    $('#torznab_cap').replaceOptions(data.categories);
                    if (data.params) {
                        torznabProviders[id][4] = data.params.toString();
                        $('#torznab_caps').val(data.params);
                    }
                }
                $(this).makeTorznabProviderString();
            });
        }
    };

    $.fn.deleteNewznabProvider = function(id) {
        $('#editANewznabProvider option[value=' + id + ']').remove();
        delete newznabProviders[id];
        $(this).populateNewznabSection();
        $('li').remove('#' + id);
        $(this).makeNewznabProviderString();
    };

    $.fn.deleteTorrentRssProvider = function(id) {
        $('#editATorrentRssProvider option[value=' + id + ']').remove();
        delete torrentRssProviders[id];
        $(this).populateTorrentRssSection();
        $('li').remove('#' + id);
        $(this).makeTorrentRssProviderString();
    };

    $.fn.deleteTorznabProvider = function(id) {
        $('#editATorznabProvider option[value=' + id + ']').remove();
        delete torznabProviders[id];
        $(this).populateTorznabSection();
        $('li').remove('#' + id);
        $(this).makeTorznabProviderString();
    };

    $.fn.populateNewznabSection = function() {
        var selectedProvider = $('#editANewznabProvider :selected').val();
        var data = '';
        var isDefault = '';
        var chosenCats = '';

        if (selectedProvider === 'addNewznab') {
            data = ['', '', ''];
            isDefault = 0;
            $('#newznab_add_div').show();
            $('#newznab_update_div').hide();
            $('#newznabcapdiv').hide();
            $('#newznab_cat option').each(function() {
                $(this).remove();
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
        var newCatOptions = [];
        if (chosenCats) {
            chosenCats.forEach(function(cat) {
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

    $.fn.populateTorrentRssSection = function() {
        var selectedProvider = $('#editATorrentRssProvider :selected').val();
        var data = '';

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

    $.fn.populateTorznabSection = function() {
        var selectedProvider = $('#editATorznabProvider :selected').val();
        var data = '';
        var chosenCats = '';

        if (selectedProvider === 'addTorznab') {
            data = ['', '', '', ''];
            $('#torznab_add_div').show();
            $('#torznab_update_div').hide();
            $('#torznabcapdiv').hide();
            $('#torznabcapsdiv').hide();
            $('#torznab_cat option').each(function() {
                $(this).remove();
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
        var newCatOptions = [];
        if (chosenCats) {
            chosenCats.forEach(function(cat) {
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

    $.fn.makeNewznabProviderString = function() {
        var provStrings = [];

        for (var id in newznabProviders) {
            if ({}.hasOwnProperty.call(newznabProviders, id)) {
                provStrings.push(newznabProviders[id][1].join('|'));
            }
        }

        $('#newznab_string').val(provStrings.join('!!!'));
    };

    $.fn.makeTorrentRssProviderString = function() {
        var provStrings = [];
        for (var id in torrentRssProviders) {
            if ({}.hasOwnProperty.call(torrentRssProviders, id)) {
                provStrings.push(torrentRssProviders[id].join('|'));
            }
        }

        $('#torrentrss_string').val(provStrings.join('!!!'));
    };

    $.fn.makeTorznabProviderString = function() {
        var provStrings = [];

        for (var id in torznabProviders) {
            if ({}.hasOwnProperty.call(torznabProviders, id)) {
                provStrings.push(torznabProviders[id].join('|'));
            }
        }

        $('#torznab_string').val(provStrings.join('!!!'));
    };

    $.fn.refreshProviderList = function() {
        var idArr = $('#provider_order_list').sortable('toArray');
        var finalArr = [];
        $.each(idArr, function(key, val) {
            var checked = $('#enable_' + val).is(':checked') ? '1' : '0';
            finalArr.push(val + ':' + checked);
        });

        $('#provider_order').val(finalArr.join(' '));
        $(this).refreshEditAProvider();
    };

    $.fn.refreshEditAProvider = function() {
        $('#provider-list').empty();

        var idArr = $('#provider_order_list').sortable('toArray');
        var finalArr = [];
        $.each(idArr, function(key, val) {
            if ($('#enable_' + val).prop('checked')) {
                finalArr.push(val);
            }
        });

        if (finalArr.length > 0) {
            $('<select>').prop('id', 'editAProvider').addClass('form-control input-sm').appendTo('#provider-list');
            for (var i = 0, len = finalArr.length; i < len; i++) {
                var provider = finalArr[i];
                $('#editAProvider').append($('<option>').prop('value', provider).text($.trim($('#' + provider).text()).replace(/\s\*$/, '').replace(/\s\*\*$/, '')));
            }
        } else {
            document.getElementsByClassName('component-desc')[0].innerHTML = 'No providers available to configure.';
        }

        $(this).showHideProviders();
    };

    $(this).on('change', '.newznab_api_key', function() {
        var providerId = $(this).prop('id');
        providerId = providerId.substring(0, providerId.length - '_hash'.length);

        var url = $('#' + providerId + '_url').val();
        var cat = $('#' + providerId + '_cat').val();
        var key = $(this).val();

        $(this).updateNewznabProvider(providerId, url, key, cat);
    });

    $('#newznab_api_key, #newznab_url').on('change', function() {
        var selectedProvider = $('#editANewznabProvider :selected').val();
        if (selectedProvider === 'addNewznab') {
            return;
        }

        var url = $('#newznab_url').val();
        var apiKey = $('#newznab_api_key').val();

        newznabProviders[selectedProvider][1] = url;
        newznabProviders[selectedProvider][2] = apiKey;

        $(this).makeNewznabProviderString();
    });

    $('#torrentrss_url, #torrentrss_cookies, #torrentrss_title_tag').on('change', function() {
        var selectedProvider = $('#editATorrentRssProvider :selected').val();
        if (selectedProvider === 'addTorrentRss') {
            return;
        }

        var url = $('#torrentrss_url').val();
        var cookies = $('#torrentrss_cookies').val();
        var titleTag = $('#torrentrss_title_tag').val();

        $(this).updateTorrentRssProvider(selectedProvider, url, cookies, titleTag);
    });

    $('#torznab_api_key, #torznab_url').on('change', function() {
        var selectedProvider = $('#editATorznabProvider :selected').val();
        if (selectedProvider === 'addTorznab') {
            return;
        }

        var url = $('#torznab_url').val();
        var apiKey = $('#torznab_api_key').val();

        torznabProviders[selectedProvider][1] = url;
        torznabProviders[selectedProvider][2] = apiKey;

        $(this).makeTorznabProviderString();
    });

    $('body').on('change', '#editAProvider', function() {
        $(this).showHideProviders();
    });

    $('#editANewznabProvider').on('change', function() {
        $('#newznab_cap option').each(function() {
            $(this).remove();
        });
        $('.updating_categories').empty();
        $(this).populateNewznabSection();
    });

    $('#editATorrentRssProvider').on('change', function() {
        $(this).populateTorrentRssSection();
    });

    $('#editATorznabProvider').on('change', function() {
        $('#torznab_cap option').each(function() {
            $(this).remove();
        });
        $('.updating_categories').empty();
        $(this).populateTorznabSection();
    });

    $(this).on('click', '.provider_enabler', function() {
        $(this).refreshProviderList();
    });

    $('#newznab_cat_update').on('click', function() {
        var selectedProvider = $('#editANewznabProvider :selected').val();

        var url = $('#newznab_url').val();
        var apiKey = $('#newznab_api_key').val();
        var cats = $('#newznab_cat option').map(function(i, opt) {
            return $(opt).text();
        }).toArray().join(',');

        $('#newznab_cat option:not([value])').remove();

        $(this).updateNewznabProvider(selectedProvider, url, apiKey, cats);
    });

    $('#torznab_cat_update').on('click', function() {
        var selectedProvider = $('#editATorznabProvider :selected').val();

        var url = $('#torznab_url').val();
        var apiKey = $('#torznab_api_key').val();
        var cats = $('#torznab_cat option').map(function(i, opt) {
            return $(opt).text();
        }).toArray().join(',');
        var caps = $('#torznab_caps').val();

        $('#torznab_cat option:not([value])').remove();

        $(this).updateTorznabProvider(selectedProvider, url, apiKey, cats, caps);
    });

    $('#newznab_cat_select').on('click', function() {
        var selectedProvider = $('#editANewznabProvider :selected').val();
        var newOptions = [];
        // When the update botton is clicked, loop through the capabilities list
        // and copy the selected category id's to the category list on the right.
        $('#newznab_cap option:selected').each(function() {
            var selectedCat = $(this).val();
            newOptions.push({
                text: selectedCat,
                value: selectedCat
            });
        });
        if (newOptions.length > 0) {
            $('#newznab_cat').replaceOptions(newOptions);
        }

        var cats = $('#newznab_cat option').map(function(i, opt) {
            return $(opt).text();
        }).toArray().join(',');

        $('#newznab_cat option:not([value])').remove();
        newznabProviders[selectedProvider][1][3] = cats;

        $(this).makeNewznabProviderString();
    });

    $('#torznab_cat_select').on('click', function() {
        var selectedProvider = $('#editATorznabProvider :selected').val();
        var newOptions = [];
        // When the update botton is clicked, loop through the capabilities list
        // and copy the selected category id's to the category list on the right.
        $('#torznab_cap option:selected').each(function() {
            var selectedCat = $(this).val();
            newOptions.push({
                text: selectedCat,
                value: selectedCat
            });
        });
        if (newOptions.length > 0) {
            $('#torznab_cat').replaceOptions(newOptions);
        }

        var cats = $('#torznab_cat option').map(function(i, opt) {
            return $(opt).text();
        }).toArray().join(',');

        $('#torznab_cat option:not([value])').remove();
        torznabProviders[selectedProvider][3] = cats;

        $(this).makeTorznabProviderString();
    });

    $('#newznab_add').on('click', function() {
        var name = $.trim($('#newznab_name').val());
        var url = $.trim($('#newznab_url').val());
        var apiKey = $.trim($('#newznab_api_key').val());

        var cats = $.trim($('#newznab_cat option').map(function(i, opt) {
            return $(opt).text();
        }).toArray().join(','));

        if (!name || !url || !apiKey) {
            return;
        }

        var params = { kind: 'newznab', name: name, url: url };

        // Send to the form with ajax, get a return value
        $.getJSON('config/providers/canAddProvider', params, function(data) {
            if (data.error !== undefined) {
                alert(data.error); // eslint-disable-line no-alert
                return;
            }

            $('#newznabcapdiv').show();
            $(this).addNewznabProvider(data.success, name, url, apiKey, cats, 0);
            $(this).updateNewznabProvider(data.success, url, apiKey, cats);
            $('#editANewznabProvider').val(data.success);
        });
    });

    $('#torrentrss_add').on('click', function() {
        var name = $('#torrentrss_name').val();
        var url = $('#torrentrss_url').val();
        var cookies = $('#torrentrss_cookies').val();
        var titleTag = $('#torrentrss_title_tag').val();
        var params = {
            name: name,
            url: url,
            cookies: cookies,
            title_tag: titleTag // eslint-disable-line camelcase
        };

        // @TODO: Move to the API
        // send to the form with ajax, get a return value
        $.getJSON('config/providers/canAddTorrentRssProvider', params, function(data) {
            if (data.error !== undefined) {
                alert(data.error); // eslint-disable-line no-alert
                return;
            }

            $(this).addTorrentRssProvider(data.success, name, url, cookies, titleTag);
            $('#editATorrentRssProvider').val(data.success);
        });
    });

    $('#torznab_add').on('click', function() {
        var name = $.trim($('#torznab_name').val());
        var url = $.trim($('#torznab_url').val());
        var apiKey = $.trim($('#torznab_api_key').val());
        var caps = $.trim($('#torznab_caps').val());
        var cats = $.trim($('#torznab_cat option').map(function(i, opt) {
            return $(opt).text();
        }).toArray().join(','));

        if (!name || !url || !apiKey) {
            return;
        }

        var params = { kind: 'torznab', name: name, url: url, api_key: apiKey }; // eslint-disable-line camelcase

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
            $(this).addTorznabProvider(data.success, name, url, apiKey, cats, caps);
            $(this).updateTorznabProvider(data.success, url, apiKey, cats, caps);
            $('#editATorznabProvider').val(data.success);
        });
    });

    $('.newznab_delete').on('click', function() {
        var selectedProvider = $('#editANewznabProvider :selected').val();
        $(this).deleteNewznabProvider(selectedProvider);
    });

    $('.torrentrss_delete').on('click', function() {
        var selectedProvider = $('#editATorrentRssProvider :selected').val();
        $(this).deleteTorrentRssProvider(selectedProvider);
    });

    $('.torznab_delete').on('click', function() {
        var selectedProvider = $('#editATorznabProvider :selected').val();
        $(this).deleteTorznabProvider(selectedProvider);
    });

    $(this).on('change', '[class="providerDiv_tip"] input', function() {
        $('div .providerDiv [name=' + $(this).prop('name') + ']').replaceWith($(this).clone());
        $('div .providerDiv [newznab_name=' + $(this).prop('id') + ']').replaceWith($(this).clone());
    });

    $(this).on('change', '[class="providerDiv_tip"] select', function() {
        $(this).find('option').each(function() {
            if ($(this).is(':selected')) {
                $(this).prop('defaultSelected', true);
            } else {
                $(this).prop('defaultSelected', false);
            }
        });
        $('div .providerDiv [name=' + $(this).prop('name') + ']').empty().replaceWith($(this).clone());
    });

    $(this).on('change', '.enabler', function() {
        if ($(this).is(':checked')) {
            $('.content_' + $(this).prop('id')).each(function() {
                $(this).show();
            });
        } else {
            $('.content_' + $(this).prop('id')).each(function() {
                $(this).hide();
            });
        }
    });

    $('.enabler').each(function() {
        if ($(this).is(':checked')) {
            $('.content_' + $(this).prop('id')).show();
        } else {
            $('.content_' + $(this).prop('id')).hide();
        }
    });

    $.fn.makeTorrentOptionString = function(providerId) {
        var seedRatio = $('.providerDiv_tip #' + providerId + '_seed_ratio').prop('value');
        var seedTime = $('.providerDiv_tip #' + providerId + '_seed_time').prop('value');
        var processMet = $('.providerDiv_tip #' + providerId + '_process_method').prop('value');
        var optionString = $('.providerDiv_tip #' + providerId + '_option_string');

        optionString.val([seedRatio, seedTime, processMet].join('|'));
    };

    $(this).on('change', '.seed_option', function() {
        var providerId = $(this).prop('id').split('_')[0];
        $(this).makeTorrentOptionString(providerId);
    });

    $.fn.replaceOptions = function(options) {
        var self;
        var $option;

        this.empty();
        self = this;

        $.each(options, function(index, option) {
            $option = $('<option></option>').prop('value', option.value).text(option.text);
            self.append($option);
        });
    };

    // Initialization stuff
    $.fn.newznabProvidersCapabilities = [];

    $(this).showHideProviders();

    $('#provider_order_list').sortable({
        placeholder: 'ui-state-highlight',
        update: function() {
            $(this).refreshProviderList();
        }
    });

    $('#provider_order_list').disableSelection();
});
