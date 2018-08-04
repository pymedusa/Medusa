<template>
    <div id="config-textbox-content">
        <div class="form-group">
            <div class="row">
                <label :for="name" class="col-sm-2 control-label">
                    <span>{{ localLabel }}</span>
                </label>
                <div class="col-sm-10 content">
                    <input type="text" :id="localId" :name="name" v-model="localValue" :class="inputClass" />
                    <p v-for="(explanation, index) in localExplanations" :key="index">{{ explanation }}</p>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
module.exports = {
    name: 'config-textbox',
    props: {
        label: {
            type: String,
            default: ''
        },
        explanations: {
            type: Array,
            default: () => []
        },
        value: {
            type: String,
            default: ''
        },
        id: {
            type: String,
            default: ''
        },
        /**
         * Overwerite the default configured class on the <input/> element.
         */
        inputClass: {
            type: String,
            default: 'form-control input-sm max-input350'
        }

    },
    data() {
        return {
            localLabel: '',
            localExplanations: [],
            localValue: null,
            localId: '',
            name: '',
        }
    },
    mounted() {
        // Assign properties
        this.localLabel = this.label;
        this.localExplanations = this.explanations;
        this.localValue = this.value;
        this.localId = this.id;
        this.name = this.id;
    },
    computed: {
        config() {
            return this.$store.state.config;
        }
    },
    watch: {
        localValue() {
            this.$emit('update', this.localValue);
        }
    }
};
</script>

<style>
.input75 {
    width: 75px;
    margin-top: -4px;
}

.input250 {
    width: 250px;
    margin-top: -4px;
}

.input350 {
    width: 350px;
    margin-top: -4px;
}

.input450 {
    width: 450px;
    margin-top: -4px;
}
</style>
