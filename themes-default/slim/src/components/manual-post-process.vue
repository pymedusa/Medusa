<template>
    <div>
        <form name="processForm" method="post" @submit.prevent="">
            <div class="row component-group">
                <!-- <div class="component-group-desc col-xs-12 col-lg-4">
                    <p>Manual post process a file or folder. For more options related to post-processing visit <app-link href="config/postprocessing">Post-Processing</app-link></p>
                </div> -->

                <div class="col-xs-12 col-lg-8">
                    <config-template label="Process Method to be used" label-for="process_method">
                        <select id="process_method" name="process_method" v-model="processMethod" class="form-control input-sm">
                            <option v-for="option in availableMethods" :value="option.value" :key="option.value">
                                {{option.text}}
                            </option>
                        </select>
                    </config-template>

                    <config-template label="Post-Processing Dir" label-for="process_path">
                        <file-browser name="location" title="postprocess location" :initial-dir="postprocessing.showDownloadDir" @update="path = $event" />
                        <div class="clear-left"><p>Select the folder from you'd like to process files from</p></div>
                    </config-template>

                    <config-toggle-slider v-model="force" label="Force already processed files" id="force">
                        <span class="smallhelp"><i>&nbsp;(Check this to post-process files that were already post-processed)</i></span>
                    </config-toggle-slider>

                    <config-toggle-slider v-model="priority" label="Mark Dir/Files as priority download" id="priority">
                        <span class="smallhelp"><i>&nbsp;(Check this to replace the file even if it exists at higher quality)</i></span>
                    </config-toggle-slider>

                    <config-toggle-slider v-model="deleteOn" label="Delete files and folders" id="deleteOn">
                        <span class="smallhelp"><i>&nbsp;(Check this to delete files and folders like auto processing)</i></span>
                    </config-toggle-slider>

                    <config-toggle-slider :disabled="!search.general.failedDownloads.enabled" v-model="failed" label="Mark as failed" id="failed">
                        <span class="smallhelp"><i>&nbsp;(Check this to mark download as failed)</i></span>
                    </config-toggle-slider>

                    <config-toggle-slider :disabled="!postprocessing.ignoreSubs" v-model="ignoreSubs" label="Skip associated subtitles check*" id="ignoreSubs">
                        <span class="smallhelp"><i>&nbsp;(Check this to post-process when no subtitles available)</i></span>
                        <span class="smallhelp"><i>* Create a new folder in PP folder and move only the files you want to ignore subtitles for</i></span>
                    </config-toggle-slider>

                </div>
            </div>
            <input id="submit" :disabled="queueIdentifier" class="btn-medusa" type="submit" value="Process" @click="start(runAsync=false)" />
            <input id="submit" :disabled="queueIdentifier" class="btn-medusa" type="submit" value="Process Async" @click="start(runAsync=true)" />
        </form>

        <div v-if="failedMessage !== ''"><span style="color: red">{{failedMessage}}</span></div>

        <div class="row" v-if="logs.length > 0">
            <pre class="col-lg-10 col-lg-offset-2">
                <div v-for="(line, index) in logs" :key="`line-${index}`">{{ line }}</div>
            </pre>
        </div>
    </div>
</template>
<script>
import { mapActions, mapGetters, mapState } from 'vuex';
import { apiRoute } from '../api';
import { AppLink, FileBrowser } from './helpers';


export default {
    name: 'manual-post-process',
    components: {
        AppLink,
        File
    },
    data() {
        return {
            processMethod: null,
            path: '',
            force: false,
            priority: false,
            deleteOn: false,
            failed: false,
            ignoreSubs: false,
            failedMessage: '',
            logs: [],
            queueIdentifier: null
        }
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            postprocessing: state => state.config.postprocessing,
            search: state => state.config.search,
            queueitems: state => state.queue.queueitems
        }),
        ...mapGetters({
            getQueueItemsByName: 'getQueueItemsByName',
            getQueueItemsByIdentifier: 'getQueueItemsByIdentifier'
        }),
        availableMethods() {
            const { postprocessing } = this;
            const defaultMethods = [
                { value: 'copy', text: 'Copy' },
                { value: 'move', text: 'Move' },
                { value: 'hardlink', text: 'Hard Link' },
                { value: 'symlink', text: 'Symbolic Link' },
                { value: 'keeplink', text: 'Keep Link' },
            ]
            if (postprocessing.reflinkAvailable) {
                defaultMethods.push({ value: 'reflink', text: 'Reference Link' });
            }
            return defaultMethods;
        }
    },
    methods: {
        /**
         * Start postprocessing.
         */
        start(runAsync) {
            const { 
                processMethod, path, force, priority,
                deleteOn, failed, ignoreSubs
            } = this;
            this.logs = [];

            const form = new FormData();
            form.set('process_method', processMethod);
            form.set('proc_dir', path);
            form.set('force', force);
            form.set('is_priority', priority);
            form.set('delete_on', deleteOn );
            form.set('failed', failed);
            form.set('proc_type', 'manual');
            form.set('ignore_subs', ignoreSubs);
            
            if (runAsync) {
                form.set('run_async', true);
                apiRoute.post('home/postprocess/processEpisode', form)
                .then(response => {
                    if (response && response.data.status === 'success') {
                        this.logs.push(response.data.message.trim())
                        this.queueIdentifier = response.data.queueItem.identifier;
                    } else {
                        if (response && response.data.message) {
                            this.failedMessage = response.data.message;
                        } else {
                            this.failedMessage = 'Something went wrong, check logs';
                        }
                    }
                })
            } else {
                form.set('run_sync', true);
                apiRoute.post('home/postprocess/processEpisode', form)
                .then(response => {
                    if (response && response.data.status === 'success') {
                        this.logs = [...this.logs, ...response.data.output];
                    }
                })
            }
        }
    },
    watch: {
        'postprocessing.processMethod': function(value) {
            if (value) {
                debugger;
                this.processMethod = value;
            }
        },
        'postprocessing.showDownloadDir': function(value) {
            if (value) {
                this.path = value;
            }
        },
        queueitems(queueItems) {
            queueItems.filter(item => item.identifier === this.queueIdentifier).forEach(item => {
                if (!item.success) {
                    this.logs.push(`Started Post-processing on path: ${item.config.path}`);
                } else {
                    this.logs.push(`Finished Post-processing on path: ${item.config.path}`);
                    this.queueIdentifier = null;
                    if (item.output) {
                        this.logs = [...this.logs, ...item.output];
                    }

                }
            })
        }
    }
};
</script>

<style>

</style>
