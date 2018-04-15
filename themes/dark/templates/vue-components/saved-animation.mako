<style scoped>
    /* =========================================================================
    Style for the selectList.mako.
    Should be moved from here, when moving the .vue files.
    ========================================================================== */

    div.fade-animation p {
        position: relative;
        text-align: center;
        text-shadow: 2px 2px 2px rgba(177, 177, 177, 0.8);
        font-size: 1.5em;
        z-index: 1000;
        color: #cacaca;
        margin: 0 0 0 0;
    }

    div.fade-animation div {
        position: fixed;
        bottom: 8px;
        right: 10px;
        z-index: 1000;
        background-color: rgb(61, 61, 61);
        opacity: 0.8;
        border-radius: 5px;
        padding: 5px 10px 5px 10px;
    }

    .fade-enter-active {
        transition: opacity .8s;
    }

    .fade-leave-active {
        transition: opacity 4s;
    }

    .fade-enter, .fade-leave-to /* .fade-leave-active below version 2.1.8 */ {
        opacity: 0;
    }

</style>
<script type="text/x-template" id="saved-animation">
    <div class="saved-animation">
        <div class="fade-animation">
            <transition-group  name="fade">
                <div ref="stateDiv" v-if="sState" class="animation-background" key="background">
                    <p ref="stateText">{{sState}}</p>
                </div>
            </transition-group>
        </div>
    </div>
</script>
<script>
    // register the component
    const animation = Vue.component('saved-animation', {
        name: 'saved-animation',
        template: `#saved-animation`,
        props: ['state', 'error'],
        mounted() {
            this.sState = this.state;
            this.sError = this.error;
        },
        data: function() {
            return {
                sState: '',
                sError: ''
            }
        },
        watch: {
            // Monitor the state prop. Required as where using basic variables (boolean and string)
            // and we want to have the local variables updated.
            state() {
                this.sState = this.state;
            }
        }
    });
</script>