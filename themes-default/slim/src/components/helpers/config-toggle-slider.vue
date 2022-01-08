<template>
    <div v-if="!experimental || experimentalEnabled" id="config-toggle-slider-content">
        <div class="form-group">
            <div class="row">
                <div class="col-sm-2">
                    <label :for="id" class="control-label">
                        <span>{{ label }}</span>
                    </label>
                </div>
                <div class="col-sm-10 content">
                    <toggle-button :width="45" :height="22" v-bind="{id, name: id, disabled}" v-model="localChecked" sync @input="updateValue()" />
                    <p v-for="(explanation, index) in explanations" :key="index">{{ explanation }}</p>
                    <slot />
                    <span style="color: red" v-if="experimental">This is an experimental feature</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { ToggleButton } from 'vue-js-toggle-button';
import { mapState } from 'vuex';

export default {
    name: 'config-toggle-slider',
    components: {
        ToggleButton
    },
    props: {
        label: {
            type: String,
            required: true
        },
        id: {
            type: String,
            required: true
        },
        value: {
            type: Boolean,
            default: null
        },
        disabled: {
            type: Boolean,
            default: false
        },
        explanations: {
            type: Array,
            default: () => []
        },
        experimental: Boolean
    },
    data() {
        return {
            localChecked: null
        };
    },
    mounted() {
        const { value } = this;
        this.localChecked = value;
    },
    computed: {
        ...mapState({
            experimentalEnabled: state => state.config.general.experimental
        })
    },
    watch: {
        value() {
            const { value } = this;
            this.localChecked = value;
        }
    },
    methods: {
        updateValue() {
            const { localChecked } = this;
            this.$emit('input', localChecked, this);
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
