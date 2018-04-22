<%inherit file="/layouts/main.mako"/>
<%!
    import os.path
    import urllib
    from medusa import app
%>
<%block name="scripts">
<script>
let app;
const startVue = () => {
    app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Add Recommended Shows'
        },
        data() {
            return {
                header: 'Add Recommended Shows'
            };
        }
    });
};
</script>
</%block>
<%block name="content">
<h1 class="header">{{header}}</h1>
<div id="addShowPortal">
    <br><br>
    <app-link href="addShows/trendingShows/?traktList=anticipated" id="btnNewShow" class="btn btn-large">
        <div class="button"><div class="add-list-icon-addtrakt"></div></div>
        <div class="buttontext">
            <h3>Add From Trakt Lists</h3>
            <p>For shows that you haven't downloaded yet, this option lets you choose from a show from one of the Trakt lists to add to Medusa .</p>
        </div>
    </app-link>

    <app-link href="addShows/popularShows/" id="btnNewShow" class="btn btn-large">
        <div class="button"><div class="add-list-icon-addimdb"></div></div>
        <div class="buttontext">
            <h3>Add From IMDB's Popular Shows</h3>
            <p>View IMDB's list of the most popular shows. This feature uses IMDB's MOVIEMeter algorithm to identify popular TV Series.</p>
        </div>
    </app-link>

    <app-link href="addShows/popularAnime/" id="btnNewShow" class="btn btn-large">
        <div class="button"><div class="add-list-icon-addanime"></div></div>
        <div class="buttontext">
            <h3>Add From Anidb's Hot Anime list</h3>
            <p>View Anidb's list of the most popular anime shows. Anidb provides lists for Popular Anime, using the "Hot Anime" list.</p>
        </div>
    </app-link>

</div>
</%block>
