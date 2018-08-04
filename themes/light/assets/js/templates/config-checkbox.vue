<template>
    <div id="config-checkbox-content">
        <div class="form-group">
            <div class="row">
                <label :for="name" class="col-sm-2 control-label">
                    <span>{{ localLabel }}</span>
                </label>
                <div class="col-sm-10 content">
                    <toggle-button :width="45" :height="22" :id="localId" :name="name" v-model="localChecked" sync></toggle-button>
                    <p v-for="(explanation, index) in localExplanations" :key="index">{{ explanation }}</p>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
module.exports = {
    name: 'config-checkbox',
    props: {
        label: {
            type: String,
            default: ''
        },
        explanations: {
            type: Array,
            default: () => []
        },
        checked: {
            type: Boolean,
            default: null
        },
        id: {
            type: String,
            default: ''
        }

    },
    data() {
        return {
            localLabel: '',
            localExplanations: [],
            localChecked: null,
            localId: '',
            name: '',
        }
    },
    mounted() {
        // Assign properties
        this.localLabel = this.label;
        this.localExplanations = this.explanations;
        this.localChecked = this.checked;
        this.localId = this.id;
        this.name = this.id;
    },
    computed: {
        config() {
            return this.$store.state.config;
        }
    },
    watch: {
        localChecked() {
            this.$emit('update', this.localChecked);
        }
    }
};
</script>

<style>
/* placeholder */
</style>
