<script type="text/x-template" id="anidb-release-group-ui">
    <div id="anidb_release_group_ui_wrapper" class="top-10">
        <div class="row">
                <div class="col-sm-4 left-whitelist" >
                    <span>Whitelist</span>
                    <ul>
                        <li v-for="item in releaseWhitelist">{{ item }}</li>
                    </ul>
                </div>
                <div class="col-sm-4 center-available">
                    <span>Release groups</span>
                    <ul>
                        <li v-for="item in releaseGroups">{{ item }}</li>
                    </ul>
                </div>
                <div class="col-sm-4 right-blacklist">
                    <span>Blacklist</span>
                    <ul>
                        <li v-for="item in releaseblacklist">{{ item }}</li>
                    </ul>
                </div>
        </div>
    </div>
</script>
<script>
Vue.component('anidb-release-group-ui', {
    name: 'anidb-release-group-ui',
    template: '#anidb-release-group-ui',
    props: ['series', 'blacklist', 'whitelist', 'allGroups'],
    data() {
        return {
            // JS only
            defSeries: '12345',
            releaseblacklist: [],
            releaseWhitelist: [],
            releaseGroups: []
        };
    },
    mounted() {
        this.releaseSeries = this.series;
        this.releaseblacklist = this.blacklist;
        this.releaseWhitelist = this.whitelist;
        this.releaseGroups = this.allGroups;
    },
    methods: {
        sendValues: function() {
            this.$emit('change', this.editItems);
        }
    }
});
</script>
