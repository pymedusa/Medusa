<style scoped>
    /* =========================================================================
    Style for the selectList.mako.
    Should be moved from here, when moving the .vue files.
    ========================================================================== */

    .error {
        background-color: red!important;
    }

    .error p {
        color: white!important;
    }

    div.fade-animation p {
        position: relative;
        text-align: center;
        text-shadow: 1px 1px 1px rgba(177, 177, 177, 0.9);
        font-size: 1.5em;
        z-index: 999999;
        color: #cacaca;
        margin: 0 0 0 0;
    }

    div.fade-animation div {
        position: fixed;
        bottom: 5px;
        right: 0px;
        padding: 5px 10px 5px 10px;
        margin: 0px 5px 0px 5px;
        z-index: 999999;
        background-color: rgb(61, 61, 61, 0.75);
        border-radius: 5px;
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
<script type="text/x-template" id="saved-message">
    <div class="saved-message">
        <div class="fade-animation">
            <transition-group  name="fade">
                <div v-if="localState" class="animation-background" key="background">
                    <p>{{localState}}</p>
                </div>
                <div v-if="localError" class="animation-background error" key="background-error">
                    <p>{{localError}}</p>
                </div>
            </transition-group>
        </div>
    </div>
</script>
<script>
    // register the component
    const animation = Vue.component('saved-message', {
        name: 'saved-message',
        template: `#saved-message`,
        props: {
            state: {
                type: String,
                default: ''
            },
            error: {
                type: String,
                default: ''
            },
            timeout: {
                type: Number,
                default: 5000
            },
            minimalDisplayTime: {
                type: Number,
                default: 2000
            }
        },
        data() {
            return {
                localState: '',
                localError: '',
                lastUpdate: Date.now()
            }
        },
        mounted() {
            this.localState = this.state;
            this.localError = this.error;
        },
        watch: {
            state: function(newState, oldState) {
                const wait = this.minimalDisplayTime - (Date.now() - this.lastUpdate)
                if (wait > 0) {
                    setTimeout(() => {
                        this.localState = newState;
                        this.lastUpdate = Date.now();
                    }, wait )
                } else {
                    this.localState = newState;
                    this.lastUpdate = Date.now();
                }

                setTimeout(() => {
                    this.localState = ''
                }, this.timeout)
            },
            error: function(newState, oldState) {
                const wait = 5000 - (Date.now() - this.lastUpdate)
                if (wait > 0) {
                    setTimeout(() => {
                        this.localError = newState;
                        this.lastUpdate = Date.now();
                    }, wait )
                } else {
                    this.localError = newState;
                    this.lastUpdate = Date.now();
                }

                setTimeout(() => {
                    this.localError = '';
                }, this.timeout)
            }
        }
    });
</script>
