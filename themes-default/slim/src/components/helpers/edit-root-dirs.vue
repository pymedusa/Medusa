<template>
    <div>
        <label for="edit_root_dir">
            <table class="defaultTable" cellspacing="1" cellpadding="0" border="0">
                <thead>
                    <tr>
                        <th class="nowrap tablesorter-header">Current</th>
                        <th class="nowrap tablesorter-header">New</th>
                        <th class="nowrap tablesorter-header" style="width: 140px;">-</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="rootDir in newRootDirs" :key="rootDir.old" class="listing-default">
                        <td align="center">{{rootDir.old}}</td>
                        <td align="center" id="display_new_root_dir">{{rootDir.new}}</td>
                        <td>
                            <button class="btn-medusa edit_root_dir" @click="editRootDir(rootDir)">Edit</button>
                            <button class="btn-medusa delete_root_dir" @click="deleteRootDir(rootDir)">Delete</button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </label>
    </div>
</template>
<script>

export default {
    name: 'edit-root-dirs',
    props: {
        rootDirs: {
            type: Array,
            required: true
        }
    },
    data() {
        return {
            newRootDirs: []
        };
    },
    mounted() {
        const { rootDirs } = this;
        this.newRootDirs = rootDirs.map(rd => ({ old: rd, new: rd }));
        this.$emit('update', this.newRootDirs);
    },
    methods: {
        /**
         * Edit the selected root dir's path.
         * Select a new root dir.
         * @param {object} rootDir root directory.
         */
        editRootDir(rootDir) {
            const { $el } = this;
            $($el).nFileBrowser(path => {
                if (path.length === 0) {
                    return;
                }

                // Update selected root dir path and select it
                this.newRootDirs = this.newRootDirs.map(rd => {
                    if (rd.old === rootDir.old) {
                        return { old: rd.old, new: path };
                    }
                    return rd;
                });

                this.$emit('update', this.newRootDirs);
            }, { initialDir: rootDir.old });
        },
        deleteRootDir(rootDir) {
            // Update selected root dir path and select it
            this.newRootDirs = this.newRootDirs.map(rd => {
                if (rd.old === rootDir.old) {
                    return { old: rd.old, new: 'DELETED', delete: true };
                }
                return rd;
            });
            this.$emit('update', this.newRootDirs);
        }
    }
};
</script>
<style>
</style>
