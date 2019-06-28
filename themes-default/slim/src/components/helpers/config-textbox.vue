<template>
    <div id="config-textbox">
        <div class="form-group">
            <div class="row">
                <label :for="id" class="col-sm-2 control-label">
                    <span>{{ label }}</span>
                </label>
                <div class="col-sm-10 content">
                    <input v-bind="{id, type, name: id, class: inputClass, placeholder, disabled}" v-model="localValue" @input="input" @change="change"/>
                    <p v-for="(explanation, index) in explanations" :key="index">{{ explanation }}</p>
                    <slot></slot>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'config-textbox',
    props: {
        label: {
            type: String,
            required: true
        },
        id: {
            type: String,
            required: true
        },
        explanations: {
            type: Array,
            default: () => []
        },
        value: {
            type: String,
            default: ''
        },
        type: {
            type: String,
            default: 'text'
        },
        disabled: {
            type: Boolean,
            default: false
        },
        /**
         * Overwrite the default configured class on the <input/> element.
         */
        inputClass: {
            type: String,
            default: 'form-control input-sm max-input350'
        },
        placeholder: {
            type: String,
            default: ''
        }

    },
    data() {
        return {
            localValue: null
        };
    },
    mounted() {
        const { value } = this;
        this.localValue = value;
    },
    watch: {
        value() {
            const { value } = this;
            this.localValue = value;
        }
    },
    methods: {
        input() {
            const { localValue } = this;
            this.$emit('input', localValue);
        },
        change() {
            const { localValue } = this;
            this.$emit('change', localValue);
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
