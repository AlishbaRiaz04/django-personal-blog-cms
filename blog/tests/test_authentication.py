from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from blog.models import AuthorProfile


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )
        self.url = reverse("login")

    def test_login_page_loads(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_valid_login_logs_the_user_in(self):
        response = self.client.post(
            self.url,
            {"username": "testuser", "password": "testpassword123"},
        )

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_wrong_password_does_not_log_in(self):
        response = self.client.post(
            self.url,
            {"username": "testuser", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_returns_user_to_the_page_they_wanted(self):
        target = reverse("author_dashboard")

        response = self.client.post(
            f"{self.url}?next={target}",
            {
                "username": "testuser",
                "password": "testpassword123",
                "next": target,
            },
        )

        self.assertRedirects(
            response, target, fetch_redirect_response=False
        )

    def test_login_ignores_next_url_pointing_to_another_site(self):
        response = self.client.post(
            self.url,
            {
                "username": "testuser",
                "password": "testpassword123",
                "next": "https://evil.example.com/",
            },
        )

        self.assertRedirects(response, reverse("home"))


class ProtectedPageRedirectTests(TestCase):
    def test_anonymous_user_is_sent_to_login_with_next(self):
        for name in ["author_dashboard", "article_create", "comment_moderation"]:
            with self.subTest(page=name):
                url = reverse(name)
                response = self.client.get(url)

                self.assertRedirects(
                    response,
                    f"{reverse('login')}?next={url}",
                )


class LogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )
        self.client.force_login(self.user)

    def test_post_logs_the_user_out(self):
        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_does_not_log_the_user_out(self):
        response = self.client.get(reverse("logout"))

        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)


class SignUpTests(TestCase):
    def setUp(self):
        self.url = reverse("signup")
        self.valid_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "a-Strong-pass-9876",
            "password2": "a-Strong-pass-9876",
        }

    def test_signup_page_loads(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/signup.html")

    def test_valid_signup_creates_user_and_logs_them_in(self):
        response = self.client.post(self.url, self.valid_data)

        self.assertRedirects(response, reverse("home"))

        user = User.objects.get(username="newuser")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_signup_automatically_creates_an_author_profile(self):
        self.client.post(self.url, self.valid_data)

        user = User.objects.get(username="newuser")

        self.assertTrue(
            AuthorProfile.objects.filter(user=user).exists()
        )

    def test_new_user_can_open_article_creation_page(self):
        self.client.post(self.url, self.valid_data)

        response = self.client.get(reverse("article_create"))

        self.assertEqual(response.status_code, 200)

    def test_mismatched_passwords_do_not_create_a_user(self):
        data = {**self.valid_data, "password2": "something-else-123"}

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_signup_saves_the_email_address(self):
        self.client.post(self.url, self.valid_data)

        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "newuser@example.com")

    def test_email_is_required(self):
        data = {**self.valid_data}
        del data["email"]

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_duplicate_email_is_rejected_regardless_of_case(self):
        User.objects.create_user(
            username="someone",
            email="NewUser@Example.com",
            password="x-pass-12345",
        )

        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username="newuser", password="x-pass-12345")

        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="newuser").count(), 1)

    def test_logged_in_user_is_redirected_away_from_signup(self):
        user = User.objects.create_user(username="existing", password="x-pass-12345")
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse("home"))


class NavigationTests(TestCase):
    def test_anonymous_visitor_sees_login_and_signup_links(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, reverse("login"))
        self.assertContains(response, reverse("signup"))
        self.assertNotContains(response, "Log out")

    def test_regular_user_does_not_see_author_links(self):
        user = User.objects.create_user(username="reader", password="x-pass-12345")
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Log out")
        self.assertNotContains(response, "Write Article")

    def test_author_sees_author_links(self):
        user = User.objects.create_user(username="writer", password="x-pass-12345")
        AuthorProfile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Write Article")
        self.assertContains(response, "Dashboard")