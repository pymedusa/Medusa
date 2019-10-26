<template>
    <div id="config-template-content">
        <div class="form-group">
            <div class="row">
                <label :for="labelFor" class="col-sm-2 control-label">
                    <span>{{ label }}</span>
                </label>
                <div class="col-sm-10 content">
                    <slot />
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'config-template',
    props: {
        label: {
            type: String,
            required: true
        },
        labelFor: {
            type: String,
            required: true
        }
    }
};
</script>

<style>

</style>
