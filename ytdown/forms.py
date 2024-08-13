from django import forms


class URLForm(forms.Form):
    youtube_url = forms.URLField(
        label='',
        min_length=16,
        max_length=200,
        widget=forms.URLInput(attrs={'placeholder': 'Enter YouTube URL'})
    )
