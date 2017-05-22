<template>
    <div>
    </div>
</template>

<script>
import {mapGetters} from 'vuex';

export default {
    name: 'general',
    computed: {
        ...mapGetters([
            'config'
        ])
    }
};
</script>
