<style>
    .root-dirs-selectbox,
    .root-dirs-selectbox select,
    .root-dirs-controls {
        width: 100%;
        max-width: 430px;
    }

    .root-dirs-selectbox {
        padding: 0 0 5px;
    }

    .root-dirs-controls {
        text-align: center;
    }
</style>
<script type="text/x-template" id="root-dirs-template">
    <div id="root-dirs-wrapper">
        <div class="root-dirs-selectbox">
            ## @TODO: Remove `id` and `name` attributes
            <select v-model="selectedRootDir" v-bind="$attrs" v-on="$listeners" name="rootDir" id="rootDirs" size="6">
                <option v-for="curDir in rootDirs" :value="curDir.path">{{markDefault(curDir)}}</option>
            </select>
        </div>
        <div class="root-dirs-controls">
            <button type="button" class="btn-medusa" @click.prevent="add">New</button>
            <button type="button" class="btn-medusa" @click.prevent="edit" :disabled="!selectedRootDir">Edit</button>
            <button type="button" class="btn-medusa" @click.prevent="remove" :disabled="!selectedRootDir">Delete</button>
            <button type="button" class="btn-medusa" @click.prevent="setDefault" :disabled="!selectedRootDir">Set as Default *</button>
        </div>
        ## @TODO: Remove this element (use a Vue events to watch for changes)
        <input type="text" style="display: none;" id="rootDirText" :value="rootDirsValue" />
    </div>
</script>
<script>
Vue.component('root-dirs', {
    template: '#root-dirs-template',
    inheritAttrs: false,
    data() {
        const rawRootDirs = MEDUSA.config.rootDirs;
        let rootDirs = [];
        if (rawRootDirs.length) {
            // Transform raw root dirs in the form of an array, to an array of objects
            defaultDir = parseInt(rawRootDirs[0], 10);
            rootDirs = rawRootDirs.slice(1)
                .map((rd, index) => {
                    return {
                        path: rd,
                        default: index === defaultDir,
                        selected: index === defaultDir
                    };
                });
        }

        return {
            rootDirs
        };
    },
    mounted() {
        // Emit the initial values
        this.$emit('update:root-dirs', this.rootDirs);
        this.$emit('update:root-dirs-value', this.rootDirsValue, this.rootDirs);
        // @FIXME: Temporarily trigger regular events as well
        this.$nextTick(() => {
            $('#rootDirs').trigger('change');
            $('#rootDirText').trigger('change');
        });
    },
    computed: {
        rootDirsValue() {
            if (this.defaultRootDir === null || this.rootDirs.length < 1) return '';
            const defaultIndex = this.rootDirs.findIndex(rd => rd.default);
            return defaultIndex.toString() + '|' + this.rootDirs.map(rd => rd.path).join('|');
        },
        selectedRootDir: {
            get() {
                const selectedDir = this.rootDirs.find(rd => rd.selected);
                if (!selectedDir || this.rootDirs.length === 0) return null;
                return selectedDir.path;
            },
            set(newRootDir) {
                this.rootDirs = this.rootDirs
                    .map(rd => {
                        rd.selected = (rd.path === newRootDir);
                        return rd;
                    });
            }
        },
        defaultRootDir: {
            get() {
                const defaultDir = this.rootDirs.find(rd => rd.default);
                if (!defaultDir || this.rootDirs.length === 0) return null;
                return defaultDir.path;
            },
            set(newRootDir) {
                this.rootDirs = this.rootDirs
                    .map(rd => {
                        rd.default = (rd.path === newRootDir);
                        return rd;
                    });
            }
        }
    },
    methods: {
        markDefault(rd) {
            return ((rd.path === this.defaultRootDir) ? '* ' : '') + rd.path;
        },
        add() {
            // Add a new root dir
            $(this.$el).nFileBrowser(path => {
                if (path.length === 0) return;

                // If the path is already a root dir, select it
                const found = this.rootDirs.find(rd => rd.path === path);
                if (found && found.path !== this.selectedRootDir) {
                    this.selectedRootDir = path;
                    return;
                }

                // If this the first root dir, set it as default and select it
                const isFirst = this.defaultRootDir === null;
                this.rootDirs.push({
                    path,
                    default: isFirst,
                    selected: isFirst
                });

                this.saveRootDirs();
            });
        },
        edit() {
            // Edit a root dir's path
            $(this.$el).nFileBrowser(path => {
                if (path.length === 0) return;

                // If the path is already a root dir, select it and remove the one being edited
                const found = this.rootDirs.find(rd => rd.path === path);
                if (found && found.path !== this.selectedRootDir) {
                    const wasDefault = found.default;
                    this.rootDirs = this.rootDirs
                        .reduce((accumlator, rd) => {
                            if (rd.path === this.selectedRootDir) return accumlator;
                            const isNewRootDir = rd.path === path;
                            rd.selected = isNewRootDir;
                            rd.default = wasDefault && isNewRootDir;

                            accumlator.push(rd);
                            return accumlator;
                        }, []);
                    return;
                }

                // Update selected root dir path and select it
                this.rootDirs.find(rd => rd.selected).path = path;
                this.selectedRootDir = path;

                this.saveRootDirs();
            }, { initialDir: this.selectedRootDir });
        },
        remove() {
            // Remove a root dir
            const oldDirIndex = this.rootDirs.findIndex(rd => rd.selected);
            const oldDirPath = this.selectedRootDir;

            // What would the list be like without the root dir we're removing?
            const filteredRootDirs = this.rootDirs.filter(rd => !rd.selected);

            // Pick a new selection, or null
            if (filteredRootDirs.length > 0) {
                const newSelected = (oldDirIndex > 0) ? oldDirIndex - 1 : 0;
                this.selectedRootDir = filteredRootDirs[newSelected].path;
            } else {
                this.selectedRootDir = null;
            }

            // If we're deleting the current default root dir, pick a new default, or null
            if (this.defaultRootDir !== null && oldDirPath === this.defaultRootDir) {
                this.defaultRootDir = this.selectedRootDir;
            }

            // Finally, remove the root dir from the list
            this.rootDirs = filteredRootDirs;

            this.saveRootDirs();
        },
        setDefault() {
            if (this.selectedRootDir === this.defaultRootDir) return;
            this.defaultRootDir = this.selectedRootDir;
            this.saveRootDirs();
        },
        async saveRootDirs() {
            let rootDirs = [];
            if (this.defaultRootDir !== null && this.rootDirs.length) {
                let defaultIndex;
                const paths = this.rootDirs.map((rd, index) => {
                    if (rd.default) defaultIndex = index;
                    return rd.path
                });
                rootDirs = Array.from(defaultIndex.toString()).concat(paths);
            }
            await api.patch('config/main', { rootDirs });
        }
    },
    watch: {
        rootDirs: {
            handler() {
                this.$emit('update:root-dirs', this.rootDirs);
                this.$nextTick(() => {
                    // @FIXME: Temporarily trigger a regular event as well
                    $('#rootDirs').trigger('change');
                });
            },
            deep: true,
            immediate: false
        },
        rootDirsValue() {
            this.$emit('update:root-dirs-value', this.rootDirsValue, this.rootDirs);
            this.$nextTick(() => {
                // @FIXME: Temporarily trigger a regular event as well
                $('#rootDirText').trigger('change');
            });
        }
    }
});
</script>
