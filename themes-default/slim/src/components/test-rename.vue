<template>
    <div id="test-rename">
        <!-- if app.PROCESS_METHOD == 'symlink': -->
        <div v-if="postprocessing.processMethod == 'symlink'" class="text-center">
            <div class="alert alert-danger upgrade-notification hidden-print" role="alert">
                <span>WARNING: Your current process method is SYMLINK. Renaming these files will break all symlinks in your Post-Processor {{ seedLocation ? '/Seeding' : '' }} directory for this show</span>
            </div>
        </div>

        <!-- <input type="hidden" id="series-id" value="${show.indexerid}" />
        <input type="hidden" id="indexer-name" value="${show.indexer_name}" /> -->

        <backstretch :slug="showSlug" />

        <h3>Preview of the proposed name changes</h3>
        <blockquote>
            <template v-if="show.config.airByDate && postprocessing.naming.enableCustomNamingAirByDate">{{postprocessing.naming.patternAirByDate}}</template>
            <template v-else-if="show.config.sports && postprocessing.naming.enableCustomNamingSports">{{postprocessing.naming.patternSportse}}</template>
            <template v-else>{{postprocessing.naming.pattern}}</template>
        </blockquote>
        <!-- < cur_season = -1 >
        < odd = False > -->
        <h2>All Seasons</h2>
        <div class="row">
            <div class="col-md-2">
                <table id="SelectAllTable" class="defaultTable" cellspacing="1" border="0" cellpadding="0">
                    <thead>
                        <tr class="seasoncols" id="selectall">
                            <th class="col-checkbox"><input type="checkbox" class="seriesCheck" id="SelectAll"></th>
                            <th align="left" valign="top" class="nowrap">Select All</th>
                        </tr>
                    </thead>
                </table>
            </div>
            <div class="col-md-10">
                <input type="submit" value="Rename Selected" class="btn-medusa btn-success"> <app-link :href="`home/displayShow?showslug=${showSlug}`" class="btn-medusa btn-danger">Cancel Rename</app-link>
            </div>
        </div>
        <table id="testRenameTable" :class="{ summaryFanArt: layout.fanartBackground }" class="defaultTable" cellspacing="1" border="0" cellpadding="0">
         <!-- for cur_ep_obj in ep_obj_list:
        <
            curLoc = cur_ep_obj.location[len(cur_ep_obj.series.location)+1:]
            curExt = curLoc.split('.')[-1]
            newLoc = cur_ep_obj.proper_path() + '.' + curExt
        >
         if int(cur_ep_obj.season) != cur_season: -->
            <thead>
                <tr class="seasonheader" id="season-${cur_ep_obj.season}">
                    <td colspan="4">
                        <br>
                        <h2>${'Specials' if int(cur_ep_obj.season) == 0 else 'Season '+str(cur_ep_obj.season)}</h2>
                    </td>
                </tr>
                <tr class="seasoncols" id="season-${cur_ep_obj.season}-cols">
                    <th class="col-checkbox"><input type="checkbox" class="seasonCheck" id="${cur_ep_obj.season}"></th>
                    <th class="nowrap">Episode</th>
                    <th class="col-name">Old Location</th>
                    <th class="col-name">New Location</th>
                </tr>
            </thead>
            <tbody>
        <!-- <
        odd = not odd
        epStr = 's{season}e{episode}'.format(season=cur_ep_obj.season, episode=cur_ep_obj.episode)
        epList = sorted([cur_ep_obj.episode] + [x.episode for x in cur_ep_obj.related_episodes])
        if len(epList) > 1:
            epList = [min(epList), max(epList)]
        > -->
                <tr class="season-${cur_season} ${'good' if curLoc == newLoc else 'wanted'} seasonstyle">
                    <td class="col-checkbox">
                     <!-- if curLoc != newLoc: -->
                        <input type="checkbox" class="epCheck" id="{epStr}" name="{epStr}" />
                     <!-- endif -->
                    </td>
                    <td align="center" valign="top" class="nowrap">{"-".join(map(str, epList))}</td>
                    <td width="50%" class="col-name">{curLoc}</td>
                    <td width="50%" class="col-name">{newLoc}</td>
                </tr>
            </tbody>
         <!-- endfor -->
        </table><br>
        <input type="submit" value="Rename Selected" class="btn-medusa btn-success"> <app-link :href="`home/displayShow?showslug=${showSlug}`" class="btn-medusa btn-danger">Cancel Rename</app-link>
    </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex';

export default {
    name: 'test-rename',
    props: {
        slug: String
    },
    data() {
        return {};
    },
    created() {
        // We need detailed info for the xem / scene exceptions, so let's get it.
        const { showSlug } = this;
        this.getShow({ showSlug });
    },
    computed: {
        ...mapState({
            postprocessing: state => state.config.postprocessing,
            seedLocation: state => state.clients.torrents.seedLocation,
            layout: state => state.config.layout
        }),
        ...mapGetters({
            show: 'getCurrentShow'
        }),
        showSlug() {
            const { slug } = this;
            return slug || this.$route.query.showslug;
        }
    },
    methods: {
        ...mapActions({
            getShow: 'getShow'
        })
    }
};
</script>

<style
</style>
