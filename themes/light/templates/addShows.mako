<%inherit file="/layouts/main.mako"/>
<%!
    import os.path
    import urllib
    from medusa import app
%>
<%block name="content">
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<div id="addShowPortal">
    <a href="addShows/newShow/" id="btnNewShow" class="btn btn-large">
        <div class="button"><div class="add-list-icon-addnewshow"></div></div>
        <div class="buttontext">
            <h3>Add New Show</h3>
            <p>For shows that you haven't downloaded yet, this option finds a show on your preferred indexer, creates a directory for it's episodes, and adds it to Medusa.</p>
        </div>
    </a>

    <a href="addShows/existingShows/" id="btnExistingShow" class="btn btn-large">
        <div class="button"><div class="add-list-icon-addexistingshow"></div></div>
        <div class="buttontext">
            <h3>Add Existing Shows</h3>
            <p>Use this option to add shows that already have a folder created on your hard drive. Medusa will scan your existing metadata/episodes and add the show accordingly.</p>
        </div>
    </a>
</div>
</%block>
