<%inherit file="/layouts/main.mako"/>
<%!
    import os.path
    import urllib
    import sickbeard
%>
<%block name="content">
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif

<div id="addShowPortal">
    <br><br>
    <a href="${srRoot}/addShows/trendingShows/?traktList=anticipated" id="btnNewShow" class="btn btn-large">
        <div class="button"><div class="add-list-icon-addtrakt"></div></div>
        <div class="buttontext">
            <h3>Add From Trakt Lists</h3>
            <p>For shows that you haven't downloaded yet, this option lets you choose from a show from one of the Trakt lists to add to Medusa .</p>
        </div>
    </a>

    <br><br>

    <a href="${srRoot}/addShows/popularShows/" id="btnNewShow" class="btn btn-large">
        <div class="button"><div class="add-list-icon-addimdb"></div></div>
        <div class="buttontext">
            <h3>Add From IMDB's Popular Shows</h3>
            <p>View IMDB's list of the most popular shows. This feature uses IMDB's MOVIEMeter algorithm to identify popular TV Series.</p>
        </div>
    </a>

    <br><br>

    <a href="${srRoot}/addShows/popularAnime" id="btnNewShow" class="btn btn-large">
        <div class="button"><div class="add-list-icon-addimdb"></div></div>
        <div class="buttontext">
            <h3>Add From Anidb's Hot Anime list</h3>
            <p>View Anidb's list of the most popular anime shows. The Anidb provides lists for Hot Anime or a random recommendation.</p>
        </div>
    </a>

</div>
</%block>
