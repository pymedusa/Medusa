<%!
    from medusa import app
    from six import text_type
%>
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <meta name="robots" content="noindex, nofollow">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="theme-color" content="#333333">
        <title>Medusa${(' - ' + title) if title and title != 'FixME' else ''}</title>
        <base href="${base_url}">
        <link rel="shortcut icon" href="images/ico/favicon.ico?v=2">
        <link rel="icon" sizes="16x16 32x32 64x64" href="images/ico/favicon.ico">
        <link rel="icon" type="image/png" sizes="196x196" href="images/ico/favicon-196.png">
        <link rel="icon" type="image/png" sizes="160x160" href="images/ico/favicon-160.png">
        <link rel="icon" type="image/png" sizes="96x96" href="images/ico/favicon-96.png">
        <link rel="icon" type="image/png" sizes="64x64" href="images/ico/favicon-64.png">
        <link rel="icon" type="image/png" sizes="32x32" href="images/ico/favicon-32.png">
        <link rel="icon" type="image/png" sizes="16x16" href="images/ico/favicon-16.png">
        <link rel="apple-touch-icon" sizes="152x152" href="images/ico/favicon-152.png">
        <link rel="apple-touch-icon" sizes="144x144" href="images/ico/favicon-144.png">
        <link rel="apple-touch-icon" sizes="120x120" href="images/ico/favicon-120.png">
        <link rel="apple-touch-icon" sizes="114x114" href="images/ico/favicon-114.png">
        <link rel="apple-touch-icon" sizes="76x76" href="images/ico/favicon-76.png">
        <link rel="apple-touch-icon" sizes="72x72" href="images/ico/favicon-72.png">
        <link rel="apple-touch-icon" href="images/ico/favicon-57.png">

        ## Webpack-imported CSS files
        <link rel="stylesheet" type="text/css" href="css/vendors.css?${sbPID}"/>

        <link rel="stylesheet" type="text/css" href="css/vender.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/browser.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/lib/jquery-ui-1.10.4.custom.min.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/style.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/themed.css?${sbPID}" />
    </head>
    <body web-root="${app.WEB_ROOT}" style="display: none;">
        <nav class="navbar navbar-default navbar-fixed-top hidden-print" role="navigation">
            <div class="container-fluid">
                <div class="navbar-header">
                    <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#nav-collapsed">
                        <span class="sr-only">Toggle navigation</span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                    </button>
                    <a class="navbar-brand" href="apibuilder/" title="Medusa">
                        <img alt="Medusa" src="images/medusa.png" style="height: 50px;" class="img-responsive pull-left" />
                        <p class="navbar-text hidden-xs">${title}</p>
                    </a>
                </div>
                <div class="collapse navbar-collapse" id="nav-collapsed">
                    <div class="btn-group navbar-btn" data-toggle="buttons">
                        <label class="btn-medusa btn-primary">
                            <input autocomplete="off" id="option-profile" type="checkbox" /> Profile
                        </label>
                        <label class="btn-medusa btn-primary">
                            <input autocomplete="off" id="option-jsonp" type="checkbox" /> JSONP
                        </label>
                    </div>
                    <ul class="nav navbar-nav navbar-right">
                        <li><a href="home/">Back to Medusa</a></li>
                    </ul>
                    <form class="navbar-form navbar-right">
                        <div class="form-group">
                            <input autocomplete="off" class="form-control" id="command-search" placeholder="Command name" type="search"/>
                        </div>
                    </form>
                </div>
            </div>
        </nav>
        <div id="content" style="margin-top: 50px;">
            <div class="panel-group" id="commands_list">
                % for command in sorted(commands):
                <%
                    command_id = command.replace('.', '-')
                    help = commands[command]((), {'help': 1}).run()
                %>
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">
                            <a data-toggle="collapse" data-parent="#commands_list" href="#command-${command_id}">${command}</a>
                        </h4>
                    </div>
                    <div class="panel-collapse collapse" id="command-${command_id}">
                        <div class="panel-body">
                            <blockquote>${help['message']}</blockquote>
                            % if help['data']['optionalParameters'] or help['data']['requiredParameters']:
                            <h4>Parameters</h4>
                            <table class="tablesorter">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Required</th>
                                    <th>Description</th>
                                    <th>Type</th>
                                    <th>Default value</th>
                                    <th>Allowed values</th>
                                </tr>
                            </thead>
                            ${display_parameters_doc(help['data']['requiredParameters'], True)}
                            ${display_parameters_doc(help['data']['optionalParameters'], False)}
                            </table>
                            % endif
                            <h4>Playground</h4>
                            URL: <kbd id="command-${command_id}-base-url">/api/v1/${apikey}/?cmd=${command}</kbd><br>
                            % if help['data']['requiredParameters']:
                                Required parameters: ${display_parameters_playground(help['data']['requiredParameters'], True, command_id)}<br>
                            % endif
                            % if help['data']['optionalParameters']:
                                Optional parameters: ${display_parameters_playground(help['data']['optionalParameters'], False, command_id)}<br>
                            % endif
                            <button class="btn-medusa btn-primary" data-action="api-call" data-command-name="${command_id}" data-base-url="command-${command_id}-base-url" data-target="#command-${command_id}-response" data-time="#command-${command_id}-time" data-url="#command-${command_id}-url">Call API</button><br>
                            <div class="result-wrapper hidden">
                                <div class="clearfix">
                                    <span class="pull-left">
                                        Response: <strong id="command-${command_id}-time"></strong><br>
                                        URL: <kbd id="command-${command_id}-url"></kbd>
                                    </span>
                                    <span class="pull-right">
                                        <button class="btn-medusa btn-default" data-action="clear-result" data-target="#command-${command_id}-response">Clear</button>
                                    </span>
                                </div>
                                <pre><code id="command-${command_id}-response"></code></pre>
                            </div>
                        </div>
                    </div>
                </div>
                % endfor
            </div>
        </div>
        <script type="text/javascript">
        var commands = ${sorted([text_type(_) for _ in commands])};
        var episodes = ${episodes};
        </script>

        ## These contain all the Webpack-imported modules
        <script src="js/vendors.js?${sbPID}"></script>
        <script src="js/medusa-runtime.js?${sbPID}"></script>
        <script src="js/index.js?${sbPID}"></script>

        <script src="js/vender.min.js?${sbPID}"></script>
        <script src="js/apibuilder.js?${sbPID}"></script>
    </body>
</html>
<%def name="display_parameters_doc(parameters, required)">
<tbody>
% for parameter in parameters:
    <% parameter_help = parameters[parameter] %>
    <tr>
        <td>
            % if required:
                <strong>${parameter}</strong>
            % else:
                ${parameter}
            % endif
        </td>
        <td class="text-center">
            % if required:
                <span class="glyphicon glyphicon-ok text-success" title="Yes"></span>
            % else:
                <span class="glyphicon glyphicon-remove text-muted" title="No"></span>
            % endif
        </td>
        <td>${parameter_help.get('desc', '')}</td>
        <td>${parameter_help.get('type', '')}</td>
        <td>${parameter_help.get('defaultValue', '')}</td>
        <td>${parameter_help.get('allowedValues', '')}</td>
    </tr>
% endfor
</tbody>
</%def>
<%def name="display_parameters_playground(parameters, required, command)">
<div class="form-inline">
    % for parameter in parameters:
    <%
        parameter_help = parameters[parameter]
        allowed_values = parameter_help.get('allowedValues', '')
        type = parameter_help.get('type', '')
    %>
    % if isinstance(allowed_values, list):
        <select class="form-control"${' multiple="multiple"' if type == 'list' else ''} name="${parameter}" data-command="${command}">
            <option>${parameter}</option>
            % if allowed_values == [0, 1]:
                <option value="0">No</option>
                <option value="1">Yes</option>
            % else:
                % for allowed_value in allowed_values:
                <option value="${allowed_value}">${allowed_value}</option>
                % endfor
            % endif
        </select>
    % elif parameter == 'indexerid':
        <select class="form-control" name="${parameter}" data-action="update-seasons" data-command="${command}">
            <option>${parameter}</option>
            % for show in shows:
            <option value="${show.indexerid}">${show.name}</option>
            % endfor
        </select>
        % if 'season' in parameters:
        <select class="form-control hidden" name="season" data-action="update-episodes" data-command="${command}">
            <option>season</option>
        </select>
        % endif
        % if 'episode' in parameters:
        <select class="form-control hidden" name="episode" data-command="${command}">
            <option>episode</option>
        </select>
        % endif
    % elif parameter == 'tvdbid':
        <input class="form-control" name="${parameter}" placeholder="${parameter}" type="number" data-command="${command}" />
    % elif type == 'int':
        % if parameter not in ('episode', 'season'):
        <input class="form-control" name="${parameter}" placeholder="${parameter}" type="number" data-command="${command}" />
        % endif
    % elif type == 'string':
        <input class="form-control" name="${parameter}" placeholder="${parameter}" type="text" data-command="${command}" />
    % endif
% endfor
</div>
</%def>
