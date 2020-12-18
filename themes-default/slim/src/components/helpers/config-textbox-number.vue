<template>
    <div id="config-textbox-number-content">
        <div class="form-group">
            <div class="row">
                <label :for="id" class="col-sm-2 control-label">
                    <span>{{ label }}</span>
                </label>
                <div class="col-sm-10 content">
                    <input type="number" v-bind="{min, max, step, id, name: id, class: inputClass, placeholder, disabled}" v-model="localValue" @input="updateValue()">
                    <p v-for="(explanation, index) in explanations" :key="index">{{ explanation }}</p>
                    <slot />
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'config-textbox-number',
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
            type: Number,
            default: 10
        },
        /**
         * Overwrite the default configured class on the <input/> element.
         */
        inputClass: {
            type: String,
            default: 'form-control input-sm input75'
        },
        min: {
            type: Number,
            default: 10
        },
        max: {
            type: Number,
            default: null
        },
        step: {
            type: Number,
            default: 1
        },
        placeholder: {
            type: String,
            default: ''
        },
        disabled: {
            type: Boolean,
            default: false
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
        updateValue() {
            const { localValue } = this;
            this.$emit('input', Number(localValue));
        }
    }
};
</script>

<style>
.form-control {
    color: rgb(0, 0, 0);
}

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

input {
    margin-bottom: 5px;
}
</style>
