<template>
    <div id="root-dirs-wrapper">
        <div class="root-dirs-selectbox">
            <!-- @TODO: Remove `id` and `name` attributes -->
            <select v-model="selectedRootDir" v-bind="$attrs" v-on="$listeners" ref="rootDirs" name="rootDir" id="rootDirs" size="6">
                <option v-for="curDir in rootDirs" :key="curDir.path" :value="curDir.path">
                    {{ markDefault(curDir) }}
                </option>
            </select>
        </div>
        <div class="root-dirs-controls">
            <button type="button" class="btn-medusa" @click.prevent="add">New</button>
            <button type="button" class="btn-medusa" @click.prevent="edit" :disabled="!selectedRootDir">Edit</button>
            <button type="button" class="btn-medusa" @click.prevent="remove" :disabled="!selectedRootDir">Delete</button>
            <button type="button" class="btn-medusa" @click.prevent="setDefault" :disabled="!selectedRootDir">Set as Default *</button>
        </div>
    </div>
</template>
<script>
/**
 * An object representing a root dir
 * @typedef {Object} rootDir
 * @property {string} path - Root dir path
 * @property {boolean} selected - Is this root dir selected?
 * @property {boolean} default - Is this the default root dir?
 */
module.exports = {
    name: 'root-dirs',
    inheritAttrs: false,
    data() {
        return {
            rootDirs: []
        };
    },
    beforeMount() {
        const { config, transformRaw } = this;
        this.rootDirs = transformRaw(config.rootDirs);
    },
    computed: {
        config() {
            return this.$store.state.config;
        },
        paths() {
            return this.rootDirs.map(rd => rd.path);
        },
        selectedRootDir: {
            get() {
                const { rootDirs } = this;
                const selectedDir = rootDirs.find(rd => rd.selected);
                if (!selectedDir || rootDirs.length === 0) {
                    return null;
                }
                return selectedDir.path;
            },
            set(newRootDir) {
                const { rootDirs } = this;
                this.rootDirs = rootDirs
                    .map(rd => {
                        rd.selected = (rd.path === newRootDir);
                        return rd;
                    });
            }
        },
        defaultRootDir: {
            get() {
                const { rootDirs } = this;
                const defaultDir = rootDirs.find(rd => rd.default);
                if (!defaultDir || rootDirs.length === 0) {
                    return null;
                }
                return defaultDir.path;
            },
            set(newRootDir) {
                const { rootDirs } = this;
                this.rootDirs = rootDirs
                    .map(rd => {
                        rd.default = (rd.path === newRootDir);
                        return rd;
                    });
            }
        }
    },
    methods: {
        /**
         * Transform raw root dirs to an array of objects
         * @param {string[]} rawRootDirs - [defaultIndex, rootDir0, rootDir1, ...]
         * @return {rootDir[]} - Root dir objects
         */
        transformRaw(rawRootDirs) {
            if (rawRootDirs.length < 2) {
                return [];
            }
            // Transform raw root dirs in the form of an array, to an array of objects
            const defaultDir = parseInt(rawRootDirs[0], 10);
            return rawRootDirs
                .slice(1)
                .map((path, index) => {
                    return {
                        path,
                        default: index === defaultDir,
                        selected: index === defaultDir
                    };
                });
        },
        /**
         * Prefix the default root dir path with '* '
         * @param {rootDir} rootDir - Current root dir object
         * @returns {string} - Modified root dir path
         */
        markDefault(rootDir) {
            if (rootDir.default) {
                return `* ${rootDir.path}`;
            }
            return rootDir.path;
        },
        /**
         * Add a new root dir
         */
        add() {
            const { $el, rootDirs, selectedRootDir, defaultRootDir, saveRootDirs } = this;
            $($el).nFileBrowser(path => {
                if (path.length === 0) {
                    return;
                }

                // If the path is already a root dir, select it
                const found = rootDirs.find(rd => rd.path === path);
                if (found && found.path !== selectedRootDir) {
                    this.selectedRootDir = path;
                    return;
                }

                // If this the first root dir, set it as default and select it
                const isFirst = defaultRootDir === null;
                rootDirs.push({
                    path,
                    default: isFirst,
                    selected: isFirst
                });

                saveRootDirs();
            });
        },
        /**
         * Edit the selected root dir's path
         */
        edit() {
            const { $el, rootDirs, selectedRootDir, saveRootDirs } = this;
            $($el).nFileBrowser(path => {
                if (path.length === 0) {
                    return;
                }

                // If the path is already a root dir, select it and remove the one being edited
                const found = rootDirs.find(rd => rd.path === path);
                if (found && found.path !== selectedRootDir) {
                    const wasDefault = found.default;
                    this.rootDirs = rootDirs
                        .reduce((accumlator, rd) => {
                            if (rd.path === selectedRootDir) {
                                return accumlator;
                            }
                            const isNewRootDir = rd.path === path;
                            rd.selected = isNewRootDir;
                            rd.default = wasDefault && isNewRootDir;

                            accumlator.push(rd);
                            return accumlator;
                        }, []);
                    return;
                }

                // Update selected root dir path and select it
                rootDirs.find(rd => rd.selected).path = path;
                this.selectedRootDir = path;

                saveRootDirs();
            }, { initialDir: selectedRootDir });
        },
        /**
         * Remove the selected root dir
         */
        remove() {
            const { rootDirs, selectedRootDir, defaultRootDir, saveRootDirs } = this;

            const oldDirIndex = rootDirs.findIndex(rd => rd.selected);
            const oldDirPath = selectedRootDir;

            // What would the list be like without the root dir we're removing?
            const filteredRootDirs = rootDirs.filter(rd => !rd.selected);

            // Pick a new selection, or null
            if (filteredRootDirs.length > 0) {
                const newSelected = (oldDirIndex > 0) ? oldDirIndex - 1 : 0;
                this.selectedRootDir = filteredRootDirs[newSelected].path;
            } else {
                this.selectedRootDir = null;
            }

            // If we're deleting the current default root dir, pick a new default, or null
            if (this.defaultRootDir !== null && oldDirPath === defaultRootDir) {
                this.defaultRootDir = selectedRootDir;
            }

            // Finally, remove the root dir from the list
            this.rootDirs = filteredRootDirs;

            saveRootDirs();
        },
        /**
         * Set the selected root dir as default
         */
        setDefault() {
            const { selectedRootDir, defaultRootDir, saveRootDirs } = this;

            if (selectedRootDir === defaultRootDir) {
                return;
            }
            this.defaultRootDir = selectedRootDir;
            saveRootDirs();
        },
        /**
         * Save the root dirs
         * @returns {Promise} - The axios Promise from the store action.
         */
        saveRootDirs() {
            const { paths, defaultRootDir } = this;

            const rootDirs = paths.slice();
            if (defaultRootDir !== null && paths.length !== 0) {
                const defaultIndex = rootDirs.findIndex(path => path === defaultRootDir);
                rootDirs.splice(0, 0, defaultIndex.toString());
            }
            return this.$store.dispatch('setConfig', {
                section: 'main',
                config: {
                    rootDirs
                }
            });
        }
    },
    watch: {
        'config.rootDirs'(rawRootDirs) {
            const { transformRaw } = this;
            this.rootDirs = transformRaw(rawRootDirs);
        },
        rootDirs: {
            handler(newValue) {
                this.$emit('update', newValue);
                this.$nextTick(() => {
                    // @FIXME: Temporarily trigger a regular event as well
                    $(this.$refs.rootDirs).trigger('change');
                });
            },
            deep: true,
            immediate: false
        },
        paths(newValue, oldValue) {
            if (JSON.stringify(newValue) !== JSON.stringify(oldValue)) {
                this.$emit('update:paths', newValue);
            }
        }
    }
};
</script>
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
