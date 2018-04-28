<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script type="text/x-template" id="add-recommended-template">
    <div>
        <h1 class="header">{{header}}</h1>
        <div id="addShowPortal">
            <app-link href="addShows/trendingShows/?traktList=anticipated" id="btnNewShow" class="btn-medusa btn-large">
                <div class="button"><div class="add-list-icon-addtrakt"></div></div>
                <div class="buttontext">
                    <h3>Add From Trakt Lists</h3>
                    <p>For shows that you haven't downloaded yet, this option lets you choose from a show from one of the Trakt lists to add to Medusa .</p>
                </div>
            </app-link>

            <app-link href="addShows/popularShows/" id="btnNewShow" class="btn-medusa btn-large">
                <div class="button"><div class="add-list-icon-addimdb"></div></div>
                <div class="buttontext">
                    <h3>Add From IMDB's Popular Shows</h3>
                    <p>View IMDB's list of the most popular shows. This feature uses IMDB's MOVIEMeter algorithm to identify popular TV Series.</p>
                </div>
            </app-link>

            <app-link href="addShows/popularAnime/" id="btnNewShow" class="btn-medusa btn-large">
                <div class="button"><div class="add-list-icon-addanime"></div></div>
                <div class="buttontext">
                    <h3>Add From Anidb's Hot Anime list</h3>
                    <p>View Anidb's list of the most popular anime shows. Anidb provides lists for Popular Anime, using the "Hot Anime" list.</p>
                </div>
            </app-link>
        </div>
    </div>
</script>
<script>
const component = {
    name: 'addRecommended',
    template: '#add-recommended-template',
    metaInfo: {
        title: 'Add Recommended Shows'
    },
    data() {
        return {
            header: 'Add Recommended Shows'
        };
    }
};

window.routes.push({
    path: '/addRecommended',
    name: 'addRecommended',
    component
});
</script>
</%block>
<%block name="content">
<router-view/>
</%block>
