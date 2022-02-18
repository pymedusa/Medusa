<template>
    <div v-if="!experimental || experimentalEnabled" id="config-template-content" :class="cls">
        <div class="form-group">
            <div class="row">
                <div class="col-sm-2">
                    <slot name="label">
                        <label :for="labelFor" class="control-label">
                            <span>{{ label }}</span>
                        </label>
                    </slot>
                </div>
                <div class="col-sm-10 content">
                    <slot />
                    <span style="color: red" v-if="experimental">This is an experimental feature</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState } from 'vuex';
export default {
    name: 'config-template',
    props: {
        label: String,
        labelFor: String,
        experimental: {
            type: Boolean,
            required: false
        },
        cls: String
    },
    computed: {
        ...mapState({
            experimentalEnabled: state => state.config.general.experimental
        })
    }
};
</script>

<style>

</style>
