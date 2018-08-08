<template>
    <select/>
</template>
<script>
import $ from 'jquery';

export default {
    name: 'language-select',
    props: {
        language: {
            type: String,
            default: 'en'
        },
        available: {
            type: String,
            default: 'en'
        },
        blank: {
            type: Boolean,
            default: false
        },
        flags: {
            type: Boolean,
            default: false
        }
    },
    mounted() {
        const vm = this;
        $(this.$el).bfhlanguages({
            flags: this.flags, language: this.language,
            available: this.available, blank: this.blank
        });

        $(this.$el).on('change', evt => {
            vm.$emit('update-language', evt.currentTarget.value);
        });
    },
    watch: {
        language() {
            $(this.$el).val(this.language);
        }
    }
};
</script>
<style>
/* placeholder */
</style>
