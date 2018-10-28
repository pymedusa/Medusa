<template>
    <div id="config-textbox-number-content">
        <div class="form-group">
            <div class="row">
                <label :for="id" class="col-sm-2 control-label">
                    <span>{{ label }}</span>
                </label>
                <div class="col-sm-10 content">
                    <input type="number" v-bind="{min, step, id, name: id, class: inputClass, placeholder}" v-model="localValue" @change="$emit('update', Number($event.target.value))"/>
                    <p v-for="(explanation, index) in explanations" :key="index">{{ explanation }}</p>
                    <slot></slot>
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
        step: {
            type: Number,
            default: 1
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
        value() {
            this.localValue = this.value;
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
</style>
