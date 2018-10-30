<template>
    <div id="config-toggle-slider-content">
        <div class="form-group">
            <div class="row">
                <label :for="id" class="col-sm-2 control-label">
                    <span>{{ label }}</span>
                </label>
                <div class="col-sm-10 content">
                    <toggle-button :width="45" :height="22" v-bind="{id, name: id, disabled}" :value="localChecked" sync @input="updateValue()"></toggle-button>
                    <p v-for="(explanation, index) in explanations" :key="index">{{ explanation }}</p>
                    <slot></slot>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'config-toggle-slider',
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
        }
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
    watch: {
        value() {
            debugger;
            const { value } = this;
            this.localChecked = value;
        }
    },
    methods: {
        updateValue() {
            const { $emit, localChecked } = this;
            $emit('update', localChecked);
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
