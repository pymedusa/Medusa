<template>
    <div v-if="showIcon" class="scroll-top-wrapper">
    	<span class="scroll-top-inner">
    		<i class="glyphicon glyphicon-circle-arrow-up"></i>
    	</span>
    </div>
</template>
<script>
export default {
    name: 'scroll-to',
    props: {
        showIcon: Boolean
    }
};
</script>
