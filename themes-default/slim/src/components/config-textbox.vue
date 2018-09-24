<template>
    <div id="config-textbox-content">
        <div class="form-group">
            <div class="row">
                <label :for="id" class="col-sm-2 control-label">
                    <span>{{ label }}</span>
                </label>
                <div class="col-sm-10 content">
                    <input :type="type" v-bind="{id, name: id}" v-model="localValue" :class="inputClass" :placeholder="placeholder"/>
                    <p v-for="(explanation, index) in explanations" :key="index">{{ explanation }}</p>
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
        this.localValue = this.value;
    },
    watch: {
        localValue() {
            this.$emit('update', this.localValue);
        },
        value() {
            this.localValue = this.value;
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
