<template>
    <div id="config-textbox">
        <div class="form-group">
            <div class="row">
                <div class="col-sm-2">
                    <label :for="id" class="control-label">
                        <span>{{ label }}</span>
                    </label>
                </div>
                <div class="col-sm-10 content">
                    <div class="parent" :class="inputClass">
                        <input v-bind="{id, type, name: id, placeholder, disabled}" v-model="localValue" @input="updateValue()">
                        <transition name="uri-error">
                            <div v-if="uriError" class="uri-error">Make sure to start your URI with http://, https://, scgi://, etc..</div>
                        </transition>
                        <slot name="warning" />
                    </div>
                    <p v-for="(explanation, index) in explanations" :key="index">{{ explanation }}</p>
                    <slot />
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
        disabled: Boolean,
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
        },
        validateUri: Boolean
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
    computed: {
        uriError() {
            const { localValue, validateUri } = this;
            if (!validateUri || !localValue) {
                return false;
            }
            return !localValue.match(/^[A-Za-z]{3,5}:\/\//);
        }
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
            this.$emit('input', localValue);
        }
    }
};
</script>

<style scoped>
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
    width: 100%;
    border: none;
}

.uri-error-enter-active,
.uri-error-leave-active {
    -moz-transition-duration: 0.3s;
    -webkit-transition-duration: 0.3s;
    -o-transition-duration: 0.3s;
    transition-duration: 0.3s;
    -moz-transition-timing-function: ease-in;
    -webkit-transition-timing-function: ease-in;
    -o-transition-timing-function: ease-in;
    transition-timing-function: ease-in;
}

.uri-error-enter-to,
.uri-error-leave {
    max-height: 100%;
}

.uri-error-enter,
.uri-error-leave-to {
    max-height: 0;
}

.parent {
    position: relative;
}

div.uri-error {
    display: block;
    overflow: hidden;
    width: 100%;
    position: absolute;
    left: 0;
    background-color: #e23636;
    padding: 0 2px 0 2px;
}
</style>
