<template>
    <div id="config-textbox-number-content">
        <div class="form-group">
            <div class="row">
                <label :for="name" class="col-sm-2 control-label">
                    <span>{{ label }}</span>
                </label>
                <div class="col-sm-10 content">
                    <input type="number" v-bind="{min, step, id}" :name="id" :value="localValue" :class="inputClass"/>
                    <p v-for="(explanation, index) in explanations" :key="index">{{ explanation }}</p>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
module.exports = {
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
            type: String,
            default: ''
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
        }
    },
    data() {
        return {
            localValue: ''
        };
    },
    mounted() {
        this.localValue = this.value;
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
