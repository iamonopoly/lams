from django import forms


class CommentForm(forms.Form):
    body = forms.CharField(
        label="",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Write a message..."}),
        max_length=2000,
    )