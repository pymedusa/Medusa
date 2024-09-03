<template>
    <div id="manage-whitelist-wrapper">
        <img v-if="true" @click="open=!open" src="images/info32.png" width="16" height="16" alt="">
        <div v-if="open" class="manage-whitelist-control-wrapper">
            <div class="title-header">
                <span class="title">{{releaseGroup}}</span>
                <svg class="manage-whitelist-close" @click="open = !open">
                    <use xlink:href="images/svg/close.svg#close" />
                </svg>
            </div>
            <form>
                <button @click.prevent="addToWhitelist">Add to whitelist</button>
                <button @click.prevent="removeFromWhitelist">Remove from whitelist</button>
                <button @click.prevent="addToBlacklist">Add to blacklist</button>
                <button @click.prevent="removeFromBlacklist">Remove from blacklist</button>
            </form>
        </div>
    </div>
</template>
<script>
import { mapActions, mapGetters } from 'vuex';

export default {
    name: 'manage-whitelist',
    data() {
        return {
            open: false
        };
    },
    props: {
        releaseGroup: {
            type: String
        }
    },
    computed: {
        ...mapGetters({
            show: 'getCurrentShow'
        })
    },
    methods: {
        ...mapActions({
            saveShowConfig: 'saveShowConfig'
        }),
        addToWhitelist() {
            const { releaseGroup, show, saveShowConfig } = this;
            if (!show.config.release.whitelist.map(item => item.toLowerCase()).includes(releaseGroup.toLowerCase())) {
                this.show.config.release.whitelist.push(releaseGroup);
                this.save(`adding release group ${releaseGroup} from the whitelist`);
            }
        },
        removeFromWhitelist() {
            const { releaseGroup, show, saveShowConfig } = this;
            if (show.config.release.whitelist.map(item => item.toLowerCase()).includes(releaseGroup.toLowerCase())) {
                this.show.config.release.whitelist = this.show.config.release.whitelist.filter(group => group.toLowerCase() !== releaseGroup.toLowerCase());
                this.save(`removing release group ${releaseGroup} from the whitelist`);
            }
        },
        addToBlacklist() {
            const { releaseGroup, show, saveShowConfig } = this;
            if (!show.config.release.blacklist.map(item => item.toLowerCase()).includes(releaseGroup.toLowerCase())) {
                this.show.config.release.blacklist.push(releaseGroup);
                this.save(`adding release group ${releaseGroup} from the blacklist`);
            }
        },
        removeFromBlacklist() {
            const { releaseGroup, show, saveShowConfig } = this;
            if (show.config.release.blacklist.map(item => item.toLowerCase()).includes(releaseGroup.toLowerCase())) {
                this.show.config.release.blacklist = this.show.config.release.blacklist.filter(group => group.toLowerCase() !== releaseGroup.toLowerCase());
                this.save(`removing release group ${releaseGroup} from the blacklist`);
            }
        },
        async save(message) {
            const { saveShowConfig, show } = this;
            try {
                await saveShowConfig({ show });                
                this.$snotify.success(
                    message,
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                debugger;
                this.$snotify.error(
                    `failed ${message}`,
                    'Error'
                );
            }
        }
    }
}
</script>
<style scoped>
.manage-whitelist-control-wrapper {
    position: absolute;
    display: flex;
    top: 25px;
    left: 0;
    background-color: rgb(51, 51, 51);
    padding: 1rem;
    border-radius: 4px;
    z-index: 1;
    flex-flow: column;
    justify-content: center;
    min-width: 20rem;
}

.title-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
}

.title {
    margin-bottom: 5px;
    text-align: center;
    color: white;
    font-weight: 700;
}

.manage-whitelist-close {
    color: red;
    width: 20px;
    height: 20px;
}

.manage-whitelist-control-wrapper form {
    display: flex;
    flex-flow: column;
    gap: 5px;
}

.manage-whitelist-control-wrapper button {
    width: 100%;
    padding: 10px 0;
}
</style>