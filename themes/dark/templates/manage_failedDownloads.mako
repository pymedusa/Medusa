<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    import os.path
    import datetime
    import re
    from medusa import providers
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import Quality, qualityPresets, qualityPresetStrings, statusStrings, Overview
    from medusa.providers.generic_provider import GenericProvider
    from medusa.helper.common import pretty_file_size
%>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Failed Downloads'
        },
        data() {
            return {
                header: 'Failed Downloads'
            };
        }
    });
};
</script>
</%block>
<%block name="content">
<h1 class="header">{{header}}</h1>
<div class="h2footer pull-right"><b>Limit:</b>
    <select name="limit" id="limit" class="form-control form-control-inline input-sm">
        <option value="100" ${'selected="selected"' if limit == '100' else ''}>100</option>
        <option value="250" ${'selected="selected"' if limit == '250' else ''}>250</option>
        <option value="500" ${'selected="selected"' if limit == '500' else ''}>500</option>
        <option value="0" ${'selected="selected"' if limit == '0' else ''}>All</option>
    </select>
</div>
<table id="failedTable" class="defaultTable tablesorter" cellspacing="1" border="0" cellpadding="0">
  <thead>
    <tr>
      <th class="nowrap" width="75%" style="text-align: left;">Release</th>
      <th width="10%">Size</th>
      <th width="14%">Provider</th>
      <th width="1%">Remove<br>
          <input type="checkbox" class="bulkCheck" id="removeCheck" />
      </th>
    </tr>
  </thead>
  <tfoot>
    <tr>
      <td rowspan="1" colspan="4"><input type="button" class="btn-medusa pull-right" value="Submit" id="submitMassRemove"></td>
    </tr>
  </tfoot>
  <tbody>
% for hItem in failedResults:
  <tr>
    <td class="nowrap">${hItem["release"]}</td>
    <td align="center">
    % if hItem["size"] != -1:
        ${pretty_file_size(hItem["size"])}
    % else:
        ?
    % endif
    </td>
    <td align="center">
    <% provider = providers.get_provider_class(GenericProvider.make_id(hItem["provider"])) %>
    % if provider is not None:
        <img src="images/providers/${provider.image_name()}" width="16" height="16" alt="${provider.name}" title="${provider.name}"/>
    % else:
        <img src="images/providers/missing.png" width="16" height="16" alt="missing provider" title="missing provider"/>
    % endif
    </td>
    <td align="center"><input type="checkbox" class="removeCheck" id="remove-${hItem["release"] | u}" /></td>
  </tr>
% endfor
  </tbody>
</table>
</%block>
