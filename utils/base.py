from unfold.admin import ModelAdmin as UnfoldModelAdmin
from django.contrib import messages
from django.shortcuts import redirect


class BaseModelAdmin(UnfoldModelAdmin):

    list_per_page = 100

    def get_actions(self, request):
        return {}

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST' and '_delete_direct' in request.POST and object_id:
            obj = self.get_object(request, object_id)
            if obj:
                obj.delete()
                messages.success(request, f'Объект "{obj}" был успешно удален.')
                return redirect('..')
        return super().changeform_view(request, object_id, form_url, extra_context)

    class Media:
        css = {
            'all': (
                'css/global.css',
                # 'css/ckeditor_custom.css',
            )
        }
