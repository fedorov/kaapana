<template>
  <layout-text v-if="example.id">
    <template v-slot:header>
      <toolbar-laptop
        :doc-id="example.id"
        :enable-auto-labeling.sync="enableAutoLabeling"
        :guideline-text="project.guideline"
        :is-reviewd="example.isConfirmed"
        :show-approve-button="project.permitApprove"
        :total="totalExample"
        class="d-none d-sm-block"
        @click:clear-label="clearTeacherList(project.id, example.id)"
        @click:review="confirm(project.id)"
      >
        <button-label-switch
          class="ms-2"
          @change="labelComponent=$event"
        />
      </toolbar-laptop>
      <toolbar-mobile
        :total="totalExample"
        class="d-flex d-sm-none"
      />
    </template>
    <template v-slot:content>
      <v-card
        v-shortkey="shortKeys"
        @shortkey="annotateOrRemoveLabel(project.id, example.id, $event.srcKey)"
      >
        <v-card-title>
          <component
            :is="labelComponent"
            :labels="labels"
            :annotations="teacherList"
            :single-label="project.singleClassClassification"
            @add="annotateLabel(project.id, example.id, $event)"
            @remove="removeTeacher(project.id, example.id, $event)"
          />
        </v-card-title>
        <v-divider />
        <v-card-text v-if="example.text.startsWith('study-id-')" class="title highlight">
          <div  style="height: 70vh; overflow: hidden">
            <iframe ref="iframe" class="ohif-frame" frameBorder="0" width="100%" height="100%" :src="study_url"></iframe>
          </div>
        </v-card-text>
        <v-card-text
          v-else
          class="title highlight"
          style="white-space: pre-wrap;"
          v-text="example.text"
        />
      </v-card>
    </template>
    <template v-slot:sidebar>
      <list-metadata :metadata="example.meta" />
    </template>
  </layout-text>
</template>

<script>
import { toRefs, useContext, useFetch, ref, watch } from '@nuxtjs/composition-api'
import LabelGroup from '@/components/tasks/textClassification/LabelGroup'
import LabelSelect from '@/components/tasks/textClassification/LabelSelect'
import LayoutText from '@/components/tasks/layout/LayoutText'
import ListMetadata from '@/components/tasks/metadata/ListMetadata'
import ToolbarLaptop from '@/components/tasks/toolbar/ToolbarLaptop'
import ToolbarMobile from '@/components/tasks/toolbar/ToolbarMobile'
import ButtonLabelSwitch from '@/components/tasks/toolbar/buttons/ButtonLabelSwitch'
import { useExampleItem } from '@/composables/useExampleItem'
import { useLabelList } from '@/composables/useLabelList'
import { useProjectItem } from '@/composables/useProjectItem'
import { useTeacherList } from '@/composables/useTeacherList'

export default {
  layout: 'workspace',

  components: {
    ButtonLabelSwitch,
    LabelGroup,
    LabelSelect,
    LayoutText,
    ListMetadata,
    ToolbarLaptop,
    ToolbarMobile
  },

  computed: {
    study_url() {
      return "/ohif/viewer/"+ this.example.text.substr(9);
    }
  },

  setup() {
    const { app, params, query } = useContext()
    const projectId = params.value.id
    const { state: projectState, getProjectById } = useProjectItem()
    const { state: exampleState, confirm, getExample } = useExampleItem()
    const {
      state: teacherState,
      annotateLabel,
      annotateOrRemoveLabel,
      autoLabel,
      clearTeacherList,
      getTeacherList,
      removeTeacher
    } = useTeacherList(app.$services.textClassification)
    const enableAutoLabeling = ref(false)
    const { state: labelState, getLabelList, shortKeys } = useLabelList()
    const labelComponent = ref('label-group')

    getLabelList(projectId)
    getProjectById(projectId)

    const { fetch } = useFetch(async() => {
      await getExample(
        projectId,
        query.value
      )
      if (enableAutoLabeling.value) {
        try {
          await autoLabel(projectId, exampleState.example.id)
        } catch(e) {
          enableAutoLabeling.value = false
          alert(e.response.data.detail)
        }
      } else {
        await getTeacherList(projectId, exampleState.example.id)
      }
    })
    watch(query, fetch)

    return {
      ...toRefs(labelState),
      ...toRefs(projectState),
      ...toRefs(teacherState),
      ...toRefs(exampleState),
      confirm,
      annotateLabel,
      annotateOrRemoveLabel,
      clearTeacherList,
      enableAutoLabeling,
      labelComponent,
      removeTeacher,
      shortKeys,
    }
  },

  validate({ params, query }) {
    return /^\d+$/.test(params.id) && /^\d+$/.test(query.page)
  }
}
</script>

<style scoped>
  .ohif-frame{
    position: relative;
    top: -40px;
  }
</style>
